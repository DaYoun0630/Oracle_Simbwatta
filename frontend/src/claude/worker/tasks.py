"""
Celery tasks for ML processing pipelines.

This module contains async tasks for:
- Voice recording processing (Whisper + wav2vec2 + BERT + Kiwi → RandomForest)
- MRI scan processing (3D CNN + ResNet)
"""

import os
import json
import tempfile
from datetime import datetime
from uuid import uuid4

from celery import Celery
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

# Initialize Celery app
app = Celery(
    'mci-worker',
    broker=os.getenv('REDIS_URL', 'redis://redis:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://redis:6379/0')
)

# Configure Celery
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    worker_prefetch_multiplier=1,  # Process one task at a time
)


def _get_minio_client():
    """Create MinIO client for file downloads."""
    from minio import Minio
    return Minio(
        os.getenv("MINIO_ENDPOINT", "minio:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        secure=False,
    )


def _get_db_connection():
    """Create sync database connection for worker tasks."""
    import psycopg2
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/mci")
    return psycopg2.connect(db_url)


@app.task(bind=True, name='process_voice_recording')
def process_voice_recording(self, recording_id: str, patient_id: str, file_path: str):
    """
    Process voice recording for MCI assessment.

    Pipeline:
    1. Download audio from MinIO
    2. Transcribe with Whisper (Korean)
    3. Extract audio embeddings (wav2vec2)
    4. Extract text embeddings (klue/bert-base)
    5. Extract linguistic features (Kiwi)
    6. Concatenate → 1561 features
    7. Impute + RandomForest prediction
    8. Store results in database

    Args:
        recording_id: UUID of the recording
        patient_id: UUID of the patient
        file_path: Object name in MinIO (voice-recordings bucket)
    """
    temp_path = None
    try:
        logger.info(f"Starting voice processing for recording {recording_id}")

        # Step 1: Download audio from MinIO
        minio_client = _get_minio_client()
        temp_fd, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(temp_fd)

        logger.info(f"Downloading from MinIO: voice-recordings/{file_path}")
        minio_client.fget_object("voice-recordings", file_path, temp_path)

        # Step 2-6: Feature extraction pipeline
        from .feature_extractor import extract_all_features
        transcript, features, linguistic_detail = extract_all_features(temp_path)

        logger.info(f"Features extracted: {features.shape[0]} dims, transcript: {len(transcript)} chars")

        # Step 7: Model inference
        from .model_inference import predict
        result = predict(features)

        # Step 8: Store results in database
        conn = _get_db_connection()
        try:
            cur = conn.cursor()
            assessment_id = str(uuid4())
            now = datetime.utcnow()

            # Build features JSONB
            features_json = json.dumps({
                "audio_embedding_dim": 768,
                "text_embedding_dim": 768,
                "linguistic_features_dim": 25,
                "total_features": int(features.shape[0]),
                "linguistic_detail": linguistic_detail,
            })

            # Insert voice assessment
            cur.execute("""
                INSERT INTO voice_assessments
                    (id, recording_id, transcript, cognitive_score,
                     mci_probability, flag, flag_reasons, features,
                     model_version, assessed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                assessment_id,
                recording_id,
                transcript,
                result["cognitive_score"],
                result["mci_probability"],
                result["flag"],
                json.dumps(result["flag_reasons"]),
                features_json,
                result["model_version"],
                now,
            ))

            # Update recording status
            cur.execute("""
                UPDATE recordings SET status = 'completed' WHERE id = %s
            """, (recording_id,))

            # Send notification to doctor if flag is not normal
            if result["flag"] != "normal":
                # Get assigned doctor
                cur.execute("""
                    SELECT p.assigned_doctor_id, d.user_id
                    FROM patients p
                    JOIN doctors d ON p.assigned_doctor_id = d.id
                    WHERE p.id = %s AND p.assigned_doctor_id IS NOT NULL
                """, (patient_id,))
                doctor_row = cur.fetchone()

                if doctor_row:
                    notification_id = str(uuid4())
                    flag_label = "경고" if result["flag"] == "warning" else "위험"
                    cur.execute("""
                        INSERT INTO notifications
                            (id, user_id, type, title, message,
                             related_patient_id, related_type, related_id, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        notification_id,
                        str(doctor_row[1]),
                        "assessment_alert",
                        f"음성 평가 {flag_label}: MCI 확률 {result['mci_probability']:.1%}",
                        f"환자의 음성 분석 결과 {result['flag']} 단계로 판정되었습니다. "
                        f"인지 점수: {result['cognitive_score']}/100",
                        patient_id,
                        "voice_assessment",
                        assessment_id,
                        now,
                    ))

            conn.commit()
            logger.info(f"Assessment saved: {assessment_id} (flag={result['flag']})")

        finally:
            conn.close()

        logger.info(f"Voice processing completed for recording {recording_id}")

        return {
            'status': 'completed',
            'recording_id': recording_id,
            'assessment_id': assessment_id,
            'label': result['label'],
            'mci_probability': result['mci_probability'],
            'cognitive_score': result['cognitive_score'],
            'flag': result['flag'],
        }

    except Exception as e:
        logger.error(f"Voice processing failed: {str(e)}", exc_info=True)

        # Update recording status to failed
        try:
            conn = _get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "UPDATE recordings SET status = 'failed' WHERE id = %s",
                (recording_id,)
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

        self.retry(exc=e, countdown=60, max_retries=3)

    finally:
        # Clean up temp file
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.task(bind=True, name='process_mri_scan')
def process_mri_scan(self, mri_id: str, patient_id: str, file_path: str):
    """
    Process MRI scan for MCI assessment.

    Pipeline:
    1. Download DICOM/NIfTI from MinIO
    2. Preprocessing (skull stripping, normalization)
    3. Extract volumetric features (hippocampus, ventricles)
    4. 3D CNN + ResNet feature extraction
    5. Generate MCI stage prediction
    6. Store results in database
    """
    try:
        logger.info(f"Starting MRI processing for scan {mri_id}")

        # TODO: Implement full MRI ML pipeline
        logger.info(f"MRI processing completed for scan {mri_id}")

        return {
            'status': 'completed',
            'mri_id': mri_id,
            'message': 'MRI processing pipeline not yet implemented'
        }

    except Exception as e:
        logger.error(f"MRI processing failed: {str(e)}")
        self.retry(exc=e, countdown=60, max_retries=3)


@app.task(name='test_celery')
def test_celery():
    """Test task to verify Celery is working."""
    logger.info("Celery test task executed successfully!")
    return {'status': 'ok', 'message': 'Celery worker is running'}


if __name__ == '__main__':
    app.start()
