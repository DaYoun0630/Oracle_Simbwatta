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
from pathlib import Path
from typing import Optional, Tuple

from celery import Celery
from celery.utils.log import get_task_logger
# Lazy import: only needed when preprocessing from scratch
# from .mri_utils import preprocess_single_subject, convert_dicom_to_nifti

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

# Define MRI Template path relative to this file
# Location: src/claude/worker/templates/mni_icbm152_t1_tal_nlin_sym_09a.nii
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MRI_TEMPLATE_PATH = os.path.join(BASE_DIR, "templates", "mni_icbm152_t1_tal_nlin_sym_09a.nii")

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
    db_url = os.getenv("DATABASE_URL", "postgresql://mci_user:change_me@postgres:5432/cognitive")
    return psycopg2.connect(db_url)


def _resolve_bucket_and_key(file_path: str, default_bucket: str = "voice-recordings") -> Tuple[str, str]:
    """
    Accepts either:
    - "voice-recordings/path/to/file.wav"
    - "s3://voice-recordings/path/to/file.wav"
    - "path/to/file.wav" (defaults bucket to default_bucket)
    """
    path = (file_path or "").strip().replace("s3://", "")
    if not path:
        raise ValueError("file_path is empty")

    if "/" not in path:
        return "voice-recordings", path

    bucket, key = path.split("/", 1)
    known = {
        "voice-recordings",
        "processed",
        "mri-scans",
        "exports",
        "mri-preprocessed",
        "mri-xai",
    }
    if bucket in known:
        return bucket, key

    # path doesn't include bucket prefix, treat it as an object key
    return default_bucket, path


def _get_preprocessed_dir() -> str:
    """Return writable local cache directory for preprocessed MRI outputs."""
    env_dir = os.getenv("MCI_PREPROCESS_CACHE_DIR") or os.getenv("MCI_PROCESSED_DIR")
    if env_dir:
        path = Path(env_dir).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    candidates = [
        Path("/tmp/mri-preprocessed-cache"),
        Path("/app/data/mri-preprocessed-cache"),
        Path("data/mri-preprocessed-cache"),
    ]
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return str(candidate)
        except Exception:
            continue

    raise RuntimeError("Could not resolve writable preprocessed cache directory")


def _get_preprocessed_bucket() -> str:
    """Bucket name for persistent preprocessed MRI artifacts."""
    bucket = os.getenv("MCI_PREPROCESSED_BUCKET", "mri-preprocessed").strip().lower()
    return bucket or "mri-preprocessed"


def _ensure_bucket_exists(minio_client, bucket: str) -> None:
    if not minio_client.bucket_exists(bucket):
        minio_client.make_bucket(bucket)


def _object_exists(minio_client, bucket: str, object_name: str) -> bool:
    try:
        minio_client.stat_object(bucket, object_name)
        return True
    except Exception:
        return False


def _download_object_if_exists(minio_client, bucket: str, object_name: str, local_path: str) -> bool:
    if not _object_exists(minio_client, bucket, object_name):
        return False
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    minio_client.fget_object(bucket, object_name, local_path)
    return True


def _upload_file_to_minio(minio_client, bucket: str, object_name: str, local_path: str) -> str:
    _ensure_bucket_exists(minio_client, bucket)
    minio_client.fput_object(bucket, object_name, local_path)
    return f"{bucket}/{object_name}"


def _download_mri_input_from_minio(file_path: str, work_dir: str, mri_id: str) -> str:
    """
    Download MRI source from MinIO and return local path.
    Supports:
    - Single object (NIfTI/DICOM)
    - Prefix/folder (DICOM series tree)
    """
    minio_client = _get_minio_client()
    bucket, key = _resolve_bucket_and_key(file_path, default_bucket="mri-scans")
    key = key.strip("/")

    # Case 1: exact object path
    try:
        minio_client.stat_object(bucket, key)
        ext = ".nii.gz" if key.endswith(".nii.gz") else Path(key).suffix
        if not ext:
            ext = ".dat"
        local_file = os.path.join(work_dir, f"{mri_id}_source{ext}")
        minio_client.fget_object(bucket, key, local_file)
        logger.info(f"Downloaded MRI object: {bucket}/{key} -> {local_file}")
        return local_file
    except Exception:
        pass

    # Case 2: prefix/folder path
    prefix = key if key.endswith("/") else f"{key}/"
    objects = [
        obj for obj in minio_client.list_objects(bucket, prefix=prefix, recursive=True)
        if getattr(obj, "object_name", None) and not obj.object_name.endswith("/")
    ]
    if not objects:
        raise FileNotFoundError(f"No MinIO object/prefix found for {bucket}/{key}")

    local_root = os.path.join(work_dir, "raw_mri")
    for obj in objects:
        rel_path = obj.object_name[len(prefix):] if obj.object_name.startswith(prefix) else obj.object_name
        target = os.path.join(local_root, rel_path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        minio_client.fget_object(bucket, obj.object_name, target)

    logger.info(f"Downloaded MRI prefix: {bucket}/{prefix} -> {local_root} ({len(objects)} objects)")
    return local_root


def _find_dicom_series_dir(root_dir: str) -> Optional[str]:
    """Find the most complete DICOM series directory under root."""
    best_dir = None
    best_count = 0
    for root, _, files in os.walk(root_dir):
        dcm_files = [name for name in files if name.lower().endswith(".dcm")]
        if len(dcm_files) > best_count:
            best_count = len(dcm_files)
            best_dir = root
    return best_dir


@app.task(bind=True, name='process_voice_recording')
def process_voice_recording(
    self,
    recording_id: str,
    patient_id: Optional[str] = None,
    file_path: Optional[str] = None,
    transcript: Optional[str] = None,
):
    """
    Process voice recording for MCI assessment.

    Pipeline:
    1. Download audio from MinIO
    2. Use transcript from chatbot/OpenAI STT (required)
    3. Extract audio embeddings (wav2vec2)
    4. Extract text embeddings (klue/bert-base)
    5. Extract linguistic features (Kiwi)
    6. Concatenate → 1561 features
    7. Impute + RandomForest prediction
    8. Store results in database

    Args:
        recording_id: UUID of the recording
        patient_id: Optional UUID of the patient. If omitted, loaded from DB.
        file_path: Optional object path. If omitted, loaded from DB recordings.file_path.
        transcript: Transcript from upstream chatbot STT (required).
    """
    temp_path = None
    try:
        logger.info(f"Starting voice processing for recording {recording_id}")

        # Resolve source metadata from DB when possible.
        conn = _get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT patient_id, file_path, transcription, uploaded_at
                FROM recordings
                WHERE recording_id = %s
                """,
                (recording_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError(f"Recording not found: {recording_id}")

            db_patient_id, db_file_path, db_transcription, db_uploaded_at = row
            if patient_id is None:
                patient_id = str(db_patient_id) if db_patient_id else None
            if file_path is None:
                file_path = db_file_path
            if (transcript is None or not str(transcript).strip()) and db_transcription:
                transcript = db_transcription

            transcript = (transcript or "").strip()
            if not transcript:
                raise RuntimeError("Transcript is required for post-STT voice pipeline")

            # Move status to processing as soon as we start.
            cur.execute(
                """
                UPDATE recordings
                SET status = 'processing',
                    uploaded_at = COALESCE(uploaded_at, %s)
                WHERE recording_id = %s
                """,
                (datetime.utcnow(), recording_id),
            )
            conn.commit()
        finally:
            conn.close()

        if not file_path:
            raise RuntimeError("No file_path available for recording")

        source_bucket, source_key = _resolve_bucket_and_key(file_path)

        # Step 1: Download audio from MinIO
        minio_client = _get_minio_client()
        temp_fd, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(temp_fd)

        logger.info(f"Downloading from MinIO: {source_bucket}/{source_key}")
        minio_client.fget_object(source_bucket, source_key, temp_path)

        # Step 2-6: Feature extraction pipeline
        from .feature_extractor import extract_features_after_stt
        transcript, features, linguistic_detail = extract_features_after_stt(
            temp_path,
            transcript=transcript,
        )

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
            confidence_score = max(result["mci_probability"], 1.0 - result["mci_probability"])

            # Build features JSONB
            features_json = json.dumps({
                "audio_embedding_dim": 768,
                "text_embedding_dim": 768,
                "linguistic_features_dim": 25,
                "total_features": int(features.shape[0]),
                "linguistic_detail": linguistic_detail,
            })
            acoustic_summary_json = json.dumps({
                "pipeline": "post_stt_rf",
                "feature_dims": {
                    "audio": 768,
                    "text": 768,
                    "linguistic": 25,
                    "total": int(features.shape[0]),
                },
            })

            # Insert voice assessment
            cur.execute("""
                INSERT INTO voice_assessments
                    (assessment_id, recording_id, transcript, cognitive_score,
                     mci_probability, flag, flag_reasons, features,
                     acoustic_summary, predicted_stage, confidence_score,
                     model_version, assessed_at, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                assessment_id,
                recording_id,
                transcript,
                result["cognitive_score"],
                result["mci_probability"],
                result["flag"],
                json.dumps(result["flag_reasons"]),
                features_json,
                acoustic_summary_json,
                "pMCI" if result["label"] == "MCI" else "CN",
                round(confidence_score, 4),
                result["model_version"],
                now,
                now,
            ))

            # Update recording status
            cur.execute("""
                UPDATE recordings
                SET status = 'completed',
                    transcription = %s,
                    uploaded_at = COALESCE(uploaded_at, %s),
                    description = NULL
                WHERE recording_id = %s
            """, (transcript, now, recording_id))

            # Send notification to doctor if flag is not normal
            if result["flag"] != "normal" and patient_id is not None:
                # Get assigned doctor
                cur.execute("""
                    SELECT p.doctor_id
                    FROM patients p
                    WHERE p.user_id = %s AND p.doctor_id IS NOT NULL
                """, (patient_id,))
                doctor_row = cur.fetchone()

                if doctor_row:
                    notification_id = str(uuid4())
                    flag_label = "경고" if result["flag"] == "warning" else "위험"
                    cur.execute("""
                        INSERT INTO notifications
                            (notification_id, user_id, type, title, message,
                             related_patient_id, related_type, related_id, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        notification_id,
                        str(doctor_row[0]),
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
                """
                UPDATE recordings
                SET status = 'failed',
                    description = %s,
                    uploaded_at = COALESCE(uploaded_at, %s)
                WHERE recording_id = %s
                """,
                (str(e)[:500], datetime.utcnow(), recording_id),
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
    temp_work_dir = None
    try:
        logger.info(f"Starting MRI processing for scan {mri_id}")
        
        # Verify template exists
        if not os.path.exists(MRI_TEMPLATE_PATH):
            raise FileNotFoundError(f"MNI Template not found at {MRI_TEMPLATE_PATH}")

        # Resolve subject id and mark task status as processing.
        conn = _get_db_connection()
        subject_id = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT subject_id FROM patients WHERE user_id = %s", (patient_id,))
            row = cur.fetchone()
            if row:
                subject_id = row[0]
            cur.execute(
                """
                UPDATE mri_assessments
                SET preprocessing_status = 'processing',
                    processed_at = NOW()
                WHERE assessment_id = %s
                """,
                (mri_id,),
            )
            conn.commit()
        finally:
            conn.close()

        # Resolve persistent object identity and local cache path.
        preprocessed_dir = _get_preprocessed_dir()
        preprocessed_bucket = _get_preprocessed_bucket()
        subject_token = subject_id or str(patient_id)
        output_name = f"{subject_token}_{mri_id}_preprocessed.nii.gz"
        output_path = os.path.join(preprocessed_dir, output_name)
        preprocessed_object_path = f"{preprocessed_bucket}/{output_name}"
        stored_file_path = preprocessed_object_path
        minio_client = _get_minio_client()

        final_path = None

        # 1) Try local cache first.
        if os.path.exists(output_path):
            final_path = output_path
            logger.info(f"Using cached preprocessed MRI: {final_path}")

        # 2) If not cached, try downloading existing preprocessed artifact from MinIO.
        if not final_path:
            if _download_object_if_exists(minio_client, preprocessed_bucket, output_name, output_path):
                final_path = output_path
                logger.info(f"Downloaded preprocessed MRI from MinIO: {preprocessed_object_path}")

        # 3) Otherwise run preprocessing from raw source.
        if not final_path:
            # Lazy import: only needed when preprocessing from scratch
            from .mri_utils import preprocess_single_subject_antspy, convert_dicom_to_nifti

            # Build local working directory for raw MRI material.
            temp_work_dir = tempfile.mkdtemp(prefix=f"mri_{mri_id}_")
            local_input_path = file_path
            if os.path.exists(file_path):
                logger.info(f"Using local MRI source: {file_path}")
            else:
                local_input_path = _download_mri_input_from_minio(file_path, temp_work_dir, mri_id)

            # Raw ingestion: if DICOM source, convert best series to NIfTI.
            current_path = local_input_path
            if os.path.isdir(local_input_path):
                series_dir = _find_dicom_series_dir(local_input_path)
                if not series_dir:
                    raise RuntimeError(f"No DICOM series found under {local_input_path}")
                nifti_path = os.path.join(temp_work_dir, f"{mri_id}.nii.gz")
                logger.info(f"Converting DICOM series {series_dir} to NIfTI {nifti_path}")
                convert_dicom_to_nifti(series_dir, nifti_path)
                current_path = nifti_path

            # ANTs preprocessing.
            ants_registration_type = os.getenv("MRI_ANTS_REGISTRATION_TYPE", "SyNRA")
            ants_clip_min = float(os.getenv("MRI_ANTS_CLIP_MIN", "-5.0"))
            ants_clip_max = float(os.getenv("MRI_ANTS_CLIP_MAX", "5.0"))
            logger.info(
                f"Running ANTs preprocessing: {current_path} -> {output_path} "
                f"(registration={ants_registration_type})"
            )
            final_path = preprocess_single_subject_antspy(
                current_path,
                output_path,
                MRI_TEMPLATE_PATH,
                registration_type=ants_registration_type,
                clip_range=(ants_clip_min, ants_clip_max),
            )

        # Ensure preprocessed artifact is persisted in MinIO bucket.
        if not _object_exists(minio_client, preprocessed_bucket, output_name):
            try:
                stored_file_path = _upload_file_to_minio(
                    minio_client,
                    preprocessed_bucket,
                    output_name,
                    final_path,
                )
                logger.info(f"Uploaded preprocessed MRI to MinIO: {stored_file_path}")
            except Exception as upload_exc:
                # Keep pipeline running even if object upload fails; store local path for traceability.
                stored_file_path = final_path
                logger.warning(
                    f"Failed to upload preprocessed MRI to MinIO ({preprocessed_object_path}): {upload_exc}. "
                    f"Using local path in DB: {final_path}"
                )

        # 3. Model Inference (Placeholder / Integration)
        logger.info(f"Running 3D CNN Inference on {final_path}")
        
        from .model_inference import predict_mri
        mri_result = predict_mri(final_path, patient_id=patient_id)
        
        predicted_stage = mri_result['label']
        confidence = mri_result['confidence']
        probabilities = mri_result['probabilities']
        
        logger.info(f"Inference Result: {predicted_stage} (Confidence: {confidence:.4f})")

        # 4. Save Results to DB
        conn = _get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE mri_assessments
                SET classification = %s,
                    predicted_stage = %s,
                    confidence = %s,
                    probabilities = %s,
                    file_path = %s,
                    preprocessing_status = 'completed',
                    processed_at = NOW()
                WHERE assessment_id = %s
            """, (
                predicted_stage,
                predicted_stage,
                confidence,
                json.dumps(probabilities),
                stored_file_path,
                mri_id,
            ))
            conn.commit()
        finally:
            conn.close()

        return {
            'status': 'completed',
            'mri_id': mri_id,
            'result': predicted_stage,
            'confidence': confidence
        }

    except Exception as e:
        logger.error(f"MRI processing failed: {str(e)}", exc_info=True)
        try:
            conn = _get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE mri_assessments
                SET preprocessing_status = 'failed',
                    processed_at = NOW()
                WHERE assessment_id = %s
                """,
                (mri_id,),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass
        self.retry(exc=e, countdown=60, max_retries=3)
    finally:
        if temp_work_dir and os.path.isdir(temp_work_dir):
            try:
                import shutil
                shutil.rmtree(temp_work_dir, ignore_errors=True)
            except Exception:
                pass


@app.task(name='test_celery')
def test_celery():
    """Test task to verify Celery is working."""
    logger.info("Celery test task executed successfully!")
    return {'status': 'ok', 'message': 'Celery worker is running'}


if __name__ == '__main__':
    app.start()
