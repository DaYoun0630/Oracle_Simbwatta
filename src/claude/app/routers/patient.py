import os
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import List, Dict, Any, Optional, Tuple
from uuid import uuid4

from celery import Celery
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, WebSocket, WebSocketDisconnect
import logging
from minio.commonconfig import CopySource
from pydantic import BaseModel

from .. import db
from ..storage import storage
from ..schemas.patient import PatientOut, PatientUpdate
from ..schemas.recording import RecordingOut, RecordingCreate
from ..schemas.assessment import VoiceAssessmentOut, MRIAssessmentOut
from ..schemas.diagnosis import DiagnosisOut
from ..schemas.training import TrainingSessionOut, Message

router = APIRouter(prefix="/api/patient", tags=["patient"])
logger = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9))


def _kst_now_naive() -> datetime:
    """Return current Korea time as naive datetime for TIMESTAMP columns."""
    return datetime.now(KST).replace(tzinfo=None)


def _transcript_bucket_name() -> str:
    """Return transcript bucket name from env with sane default."""
    bucket = (os.getenv("MINIO_TRANSCRIPT_BUCKET", "voice-transcript") or "").strip()
    return bucket or "voice-transcript"


def _resolve_bucket_and_key(path: str, default_bucket: str) -> Tuple[str, str]:
    """
    Resolve either `bucket/key`, `s3://bucket/key`, or plain `key`.
    If bucket is omitted, `default_bucket` is used.
    """
    raw = (path or "").strip().replace("s3://", "")
    if not raw:
        raise ValueError("Object path is empty")
    if "/" not in raw:
        return default_bucket, raw

    bucket, key = raw.split("/", 1)
    known_buckets = {
        "voice-recordings",
        "voice-transcript",
        "processed",
        "mri-scans",
        "exports",
        "mri-preprocessed",
        "mri-xai",
        default_bucket,
    }
    if bucket in known_buckets:
        return bucket, key
    return default_bucket, raw


def _load_transcript_text(bucket: str, key: str) -> str:
    """Download transcript text object from MinIO and return UTF-8 content."""
    response = None
    try:
        response = storage.client.get_object(bucket, key)
        text = response.read().decode("utf-8", errors="replace").strip()
    finally:
        if response is not None:
            response.close()
            response.release_conn()
    if not text:
        raise ValueError(f"Transcript object is empty: {bucket}/{key}")
    return text


def _store_transcript_text(bucket: str, key: str, transcript: str) -> str:
    """Persist transcript text to MinIO for `.wav` / `.txt` parity."""
    payload = transcript.encode("utf-8")
    if not storage.client.bucket_exists(bucket):
        storage.client.make_bucket(bucket)
    storage.client.put_object(
        bucket,
        key,
        BytesIO(payload),
        length=len(payload),
        content_type="text/plain; charset=utf-8",
    )
    return f"{bucket}/{key}"


def _copy_minio_object(
    source_bucket: str,
    source_key: str,
    dest_bucket: str,
    dest_key: str,
    content_type: Optional[str] = None,
) -> str:
    """
    Copy an object inside MinIO.
    Falls back to stream-copy when server-side copy is unavailable.
    """
    if source_bucket == dest_bucket and source_key == dest_key:
        return f"{dest_bucket}/{dest_key}"

    if not storage.client.bucket_exists(dest_bucket):
        storage.client.make_bucket(dest_bucket)

    try:
        storage.client.copy_object(
            dest_bucket,
            dest_key,
            CopySource(source_bucket, source_key),
        )
        return f"{dest_bucket}/{dest_key}"
    except Exception:
        response = None
        try:
            stat = storage.client.stat_object(source_bucket, source_key)
            response = storage.client.get_object(source_bucket, source_key)
            storage.client.put_object(
                dest_bucket,
                dest_key,
                response,
                length=int(getattr(stat, "size", 0) or 0),
                content_type=content_type or getattr(stat, "content_type", None) or "application/octet-stream",
            )
        finally:
            if response is not None:
                response.close()
                response.release_conn()
        return f"{dest_bucket}/{dest_key}"

# Celery client for dispatching ML tasks
celery_app = Celery(
    broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://redis:6379/0"),
)


# ============================================================================
# WebSocket Chat with LLM
# ============================================================================
class ConnectionManager:
    """Manages WebSocket connections for patient chat sessions."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, patient_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[str(patient_id)] = websocket

    def disconnect(self, patient_id: int):
        self.active_connections.pop(str(patient_id), None)

    async def send_message(self, patient_id: int, message: str):
        if str(patient_id) in self.active_connections:
            await self.active_connections[str(patient_id)].send_text(message)


manager = ConnectionManager()


@router.websocket("/chat")
async def chat_ws(websocket: WebSocket, patient_id: int = Query(...)):
    """
    WebSocket endpoint for real-time voice chat with LLM.

    Supports two frame types:
    - Binary frames: raw audio chunks (accumulated for ML assessment)
    - JSON frames: {"message": "text", "session_id": "optional-id"}

    On disconnect, accumulated audio is auto-saved to MinIO and the
    ML pipeline (Whisper → wav2vec2 → BERT → Kiwi → RandomForest)
    is triggered automatically via Celery.
    """
    await manager.connect(patient_id, websocket)
    audio_buffer = BytesIO()
    session_id = None
    transcript_hints: List[str] = []

    try:
        # Verify patient exists
        patient = await db.fetchrow("SELECT * FROM patients WHERE user_id = $1", patient_id)
        if not patient:
            await websocket.send_json({"error": "Patient not found"})
            await websocket.close()
            return

        while True:
            # Receive either binary (audio) or text (JSON) frame
            message = await websocket.receive()

            # Binary frame: audio chunk from microphone
            if "bytes" in message and message["bytes"]:
                audio_buffer.write(message["bytes"])
                continue

            # Text frame: JSON chat message
            if "text" in message and message["text"]:
                import json as _json
                try:
                    data = _json.loads(message["text"])
                except Exception:
                    await websocket.send_json({"error": "Invalid JSON message"})
                    continue

                user_message = data.get("message", "")
                session_id = data.get("session_id", session_id)
                provided_transcript = data.get("transcript")

                if not user_message:
                    await websocket.send_json({"error": "Empty message"})
                    continue

                if isinstance(provided_transcript, str) and provided_transcript.strip():
                    transcript_hints.append(provided_transcript.strip())
                elif user_message.strip():
                    # Fallback transcript hint: text chat payload itself.
                    transcript_hints.append(user_message.strip())

                # Create session if needed
                if not session_id:
                    session_id = str(uuid4())
                    await db.execute("""
                        INSERT INTO training_sessions (training_id, patient_id, started_at, exercise_type)
                        VALUES ($1, $2, $3, $4)
                    """, session_id, patient_id, _kst_now_naive(), "chat")

                # TODO: Call LLM service (OpenAI GPT-4o-mini with Korean optimization)
                llm_response = f"Echo: {user_message}"

                # Send response
                await websocket.send_json({
                    "response": llm_response,
                    "session_id": session_id,
                    "timestamp": datetime.now(KST).isoformat()
                })

    except WebSocketDisconnect:
        manager.disconnect(patient_id)
        now = _kst_now_naive()

        # Close training session
        if session_id:
            await db.execute("""
                UPDATE training_sessions SET ended_at = $1 WHERE training_id = $2
            """, now, session_id)

        # Auto-save audio and trigger ML pipeline
        audio_size = audio_buffer.tell()
        if audio_size > 0:
            recording_id = str(uuid4())
            object_name = f"{patient_id}/{recording_id}.wav"
            if not session_id:
                session_id = str(uuid4())
                await db.execute(
                    """
                    INSERT INTO training_sessions (training_id, patient_id, started_at, ended_at, exercise_type)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    session_id,
                    patient_id,
                    now,
                    now,
                    "chat",
                )

            # Save audio buffer to MinIO
            try:
                audio_buffer.seek(0)
                storage.client.put_object(
                    "voice-recordings",
                    object_name,
                    audio_buffer,
                    length=audio_size,
                    content_type="audio/wav",
                )
                storage_path = f"voice-recordings/{object_name}"
                merged_transcript = " ".join(t for t in transcript_hints if t).strip()
                if not merged_transcript:
                    raise ValueError("Transcript is required for voice processing")

                # Create recording entry in DB
                await db.execute("""
                    INSERT INTO recordings
                        (recording_id, training_id, patient_id, file_path,
                         file_size_bytes, format, recorded_at, uploaded_at, status,
                         transcription, exercise_type, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """, recording_id, session_id, patient_id, storage_path,
               audio_size, "wav", now, now, "pending", merged_transcript, "chat", now)

                # Dispatch Celery ML task
                celery_app.send_task(
                    "process_voice_recording",
                    args=[recording_id, patient_id, storage_path],
                    kwargs={"transcript": merged_transcript},
                )

            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f"Failed to save auto-recording: {e}", exc_info=True
                )

    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
        manager.disconnect(patient_id)


# ============================================================================
# Cognitive Exercises
# ============================================================================
@router.get("/exercises")
async def list_exercises(patient_id: int = Query(...)):
    """
    Get list of cognitive training exercises for the patient.
    Returns exercises based on patient's MCI stage.
    """
    patient = await db.fetchrow("SELECT * FROM patients WHERE user_id = $1", patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    stage_hint = patient.get("risk_level") or "unknown"

    # TODO: Return exercises based on MCI stage and Korean NLP optimization
    # For now, return static list
    exercises = [
        {
            "id": "exercise_memory_1",
            "title": "기억력 훈련 - 단어 기억하기",
            "description": "제시된 단어들을 기억하고 순서대로 말해보세요.",
            "type": "memory",
            "difficulty": "easy" if stage_hint == "low" else "medium",
            "duration_minutes": 10
        },
        {
            "id": "exercise_attention_1",
            "title": "주의력 훈련 - 패턴 찾기",
            "description": "화면에 나타나는 패턴을 찾아보세요.",
            "type": "attention",
            "difficulty": "medium",
            "duration_minutes": 15
        },
        {
            "id": "exercise_language_1",
            "title": "언어 능력 - 이야기 만들기",
            "description": "주어진 주제로 짧은 이야기를 만들어보세요.",
            "type": "language",
            "difficulty": "easy",
            "duration_minutes": 20
        }
    ]

    return {"exercises": exercises, "patient_stage": stage_hint}


# ============================================================================
# Voice Recordings
# ============================================================================
@router.post("/recordings", response_model=RecordingOut)
async def upload_recording(
    patient_id: int = Query(...),
    file: UploadFile = File(...),
    description: str = Query(None),
    transcript: Optional[str] = Query(None),
    transcript_key: Optional[str] = Query(None),
):
    """
    Upload a voice recording for cognitive assessment.
    File will be stored in MinIO and queued for ML processing.
    """
    # Verify patient exists
    patient = await db.fetchrow("SELECT * FROM patients WHERE user_id = $1", patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Validate file type
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio file")

    # Generate unique filename
    recording_id = str(uuid4())
    file_extension = file.filename.split(".")[-1] if "." in file.filename else "wav"
    object_name = f"{patient_id}/{recording_id}.{file_extension}"

    # Save to temp file first
    temp_path = f"/tmp/{recording_id}.{file_extension}"
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Upload to MinIO
    try:
        storage_path = storage.upload_file("voice-recordings", object_name, temp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
    finally:
        # Clean up temp file
        import os
        if os.path.exists(temp_path):
            os.remove(temp_path)

    # Resolve transcript from direct text or existing MinIO .txt object.
    now = _kst_now_naive()
    transcript_text = (transcript or "").strip()
    if not transcript_text and transcript_key:
        transcript_bucket = _transcript_bucket_name()
        try:
            bucket, key = _resolve_bucket_and_key(transcript_key, transcript_bucket)
            transcript_text = _load_transcript_text(bucket, key)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to load transcript_key: {e}")
    if not transcript_text:
        raise HTTPException(
            status_code=400,
            detail="transcript is required (or provide transcript_key for MinIO .txt)",
        )

    # Store transcript object in final MinIO for consistent wav/txt pairing.
    transcript_bucket = _transcript_bucket_name()
    standardized_transcript_key = f"{patient_id}/{recording_id}.txt"
    try:
        _store_transcript_text(transcript_bucket, standardized_transcript_key, transcript_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store transcript object: {e}")

    training_id = str(uuid4())
    await db.execute(
        """
        INSERT INTO training_sessions (training_id, patient_id, started_at, ended_at, exercise_type)
        VALUES ($1, $2, $3, $4, $5)
        """,
        training_id,
        patient_id,
        now,
        now,
        "upload",
    )
    storage_path = f"voice-recordings/{object_name}"
    await db.execute("""
        INSERT INTO recordings (
            recording_id, training_id, patient_id, file_path,
            file_size_bytes, format, recorded_at, uploaded_at, status,
            transcription, exercise_type, description, created_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
    """, recording_id, training_id, patient_id, storage_path, len(content), file_extension, now, now, "pending",
       transcript_text, "upload", description or "", now)

    # Queue Celery task for transcript-first post-STT pipeline.
    celery_app.send_task(
        "process_voice_recording",
        args=[recording_id, patient_id, storage_path],
        kwargs={"transcript": transcript_text},
    )

    # Keep response aligned with RecordingOut schema.
    return {
        "recording_id": recording_id,
        "patient_id": patient_id,
        "training_id": training_id,
        "file_path": storage_path,
        "duration_seconds": None,
        "file_size_bytes": len(content),
        "format": file_extension,
        "transcription": transcript_text,
        "description": description or "",
        "recorded_at": now,
        "uploaded_at": now,
        "status": "pending",
    }


@router.post("/recordings/from-minio", response_model=RecordingOut)
async def register_recording_from_minio(
    patient_id: int = Query(...),
    audio_key: str = Query(..., min_length=1),
    transcript_key: Optional[str] = Query(None),
    description: Optional[str] = Query(None),
):
    """
    Register an existing MinIO `.wav` + `.txt` pair and enqueue voice pipeline.

    This uses final project's API/DB/Redis/Celery and does not touch m_ch services.
    """
    patient = await db.fetchrow("SELECT * FROM patients WHERE user_id = $1", patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    audio_bucket, audio_object_key = _resolve_bucket_and_key(audio_key, "voice-recordings")
    if audio_bucket != "voice-recordings":
        raise HTTPException(status_code=400, detail="audio_key must point to voice-recordings bucket")

    try:
        stat = storage.client.stat_object(audio_bucket, audio_object_key)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Audio object not found: {e}")

    source_transcript_bucket = _transcript_bucket_name()
    if transcript_key:
        source_transcript_bucket, transcript_object_key = _resolve_bucket_and_key(
            transcript_key,
            source_transcript_bucket,
        )
    else:
        transcript_object_key = f"{audio_object_key.rsplit('.', 1)[0]}.txt"

    try:
        storage.client.stat_object(source_transcript_bucket, transcript_object_key)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Transcript object not found: {e}")

    recording_id = str(uuid4())
    training_id = str(uuid4())
    now = _kst_now_naive()
    file_extension = audio_object_key.split(".")[-1].lower() if "." in audio_object_key else "wav"
    storage_path = f"{audio_bucket}/{audio_object_key}"

    # Keep original object path/key exactly as source.
    try:
        transcript_text = _load_transcript_text(source_transcript_bucket, transcript_object_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load transcript object: {e}")

    await db.execute(
        """
        INSERT INTO training_sessions (training_id, patient_id, started_at, ended_at, exercise_type)
        VALUES ($1, $2, $3, $4, $5)
        """,
        training_id,
        patient_id,
        now,
        now,
        "upload",
    )
    await db.execute(
        """
        INSERT INTO recordings (
            recording_id, training_id, patient_id, file_path,
            file_size_bytes, format, recorded_at, uploaded_at, status,
            transcription, exercise_type, description, created_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        """,
        recording_id,
        training_id,
        patient_id,
        storage_path,
        int(getattr(stat, "size", 0) or 0),
        file_extension,
        now,
        now,
        "pending",
        transcript_text,
        "upload",
        description or "",
        now,
    )

    celery_app.send_task(
        "process_voice_recording",
        args=[recording_id, patient_id, storage_path],
        kwargs={"transcript": transcript_text},
    )

    return {
        "recording_id": recording_id,
        "patient_id": patient_id,
        "training_id": training_id,
        "file_path": storage_path,
        "duration_seconds": None,
        "file_size_bytes": int(getattr(stat, "size", 0) or 0),
        "format": file_extension,
        "transcription": transcript_text,
        "description": description or "",
        "recorded_at": now,
        "uploaded_at": now,
        "status": "pending",
    }


@router.get("/recordings", response_model=List[RecordingOut])
async def list_recordings(patient_id: int = Query(...), limit: int = Query(50, le=100)):
    """List all voice recordings for a patient."""
    rows = await db.fetch("""
        SELECT
            recording_id,
            patient_id,
            training_id,
            file_path,
            duration_seconds,
            file_size_bytes,
            format,
            COALESCE(recorded_at, created_at) AS recorded_at,
            COALESCE(uploaded_at, created_at) AS uploaded_at,
            COALESCE(status, 'pending') AS status
        FROM recordings
        WHERE patient_id = $1
        ORDER BY COALESCE(recorded_at, created_at) DESC
        LIMIT $2
    """, patient_id, limit)

    return [dict(r) for r in rows]


@router.get("/recordings/{recording_id}", response_model=RecordingOut)
async def get_recording(recording_id: str, patient_id: int = Query(...)):
    """Get details of a specific recording."""
    row = await db.fetchrow("""
        SELECT
            recording_id,
            patient_id,
            training_id,
            file_path,
            duration_seconds,
            file_size_bytes,
            format,
            COALESCE(recorded_at, created_at) AS recorded_at,
            COALESCE(uploaded_at, created_at) AS uploaded_at,
            COALESCE(status, 'pending') AS status
        FROM recordings
        WHERE recording_id = $1 AND patient_id = $2
    """, recording_id, patient_id)

    if not row:
        raise HTTPException(status_code=404, detail="Recording not found")

    return dict(row)


# ============================================================================
# Progress Tracking
# ============================================================================
@router.get("/progress")
async def get_progress(patient_id: int = Query(...)):
    """
    Get patient's training progress and analytics.
    Includes session count, total duration, recent activity, and trends.
    """
    # Verify patient
    patient = await db.fetchrow("SELECT * FROM patients WHERE user_id = $1", patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Get session statistics
    sessions = await db.fetch("""
        SELECT
            COUNT(*) as total_sessions,
            COUNT(CASE WHEN ended_at IS NOT NULL THEN 1 END) as completed_sessions,
            SUM(EXTRACT(EPOCH FROM (ended_at - started_at))) / 3600.0 as total_hours
        FROM training_sessions
        WHERE patient_id = $1
    """, patient_id)

    # Get recent sessions
    recent_sessions = await db.fetch("""
        SELECT training_id AS id, started_at, ended_at
        FROM training_sessions
        WHERE patient_id = $1
        ORDER BY started_at DESC
        LIMIT 10
    """, patient_id)

    # Get assessment count
    assessment_stats = await db.fetchrow("""
        SELECT
            COUNT(DISTINCT va.assessment_id) as voice_assessments,
            COUNT(DISTINCT ma.assessment_id) as mri_assessments
        FROM patients p
        LEFT JOIN recordings r ON r.patient_id = p.user_id
        LEFT JOIN voice_assessments va ON va.recording_id = r.recording_id
        LEFT JOIN mri_assessments ma ON ma.patient_id = p.user_id
        WHERE p.user_id = $1
    """, patient_id)

    stats = dict(sessions[0]) if sessions else {}

    return {
        "patient_id": patient_id,
        "current_stage": patient.get("risk_level") or "unknown",
        "sessions": {
            "total": stats.get("total_sessions", 0),
            "completed": stats.get("completed_sessions", 0),
            "total_hours": round(stats.get("total_hours", 0.0), 2),
            "recent": [dict(s) for s in recent_sessions]
        },
        "assessments": {
            "voice": assessment_stats["voice_assessments"] or 0,
            "mri": assessment_stats["mri_assessments"] or 0
        }
    }

# Alias for frontend compatibility
@router.get("/dashboard")
async def get_dashboard(patient_id: int = Query(None)):
    """Dashboard data for the patient (alias for progress)"""
    # If patient_id is not provided, it should be extracted from token in real app
    # For now, require it or use a default if testing
    if not patient_id:
        raise HTTPException(status_code=400, detail="patient_id is required")
    return await get_progress(patient_id)

# ============================================================================
# Assessments
# ============================================================================
@router.get("/assessments")
async def list_assessments(patient_id: int = Query(...), limit: int = Query(50, le=100)):
    """
    List all assessments (voice + MRI) for the patient.
    Returns combined list sorted by date.
    """
    # Get voice assessments
    voice_assessments = await db.fetch("""
        SELECT va.*
        FROM voice_assessments va
        JOIN recordings r ON va.recording_id = r.recording_id
        WHERE r.patient_id = $1
        ORDER BY va.assessed_at DESC
        LIMIT $2
    """, patient_id, limit)

    # Get MRI assessments
    mri_assessments = await db.fetch("""
        SELECT * FROM mri_assessments
        WHERE patient_id = $1
        ORDER BY processed_at DESC NULLS LAST
        LIMIT $2
    """, patient_id, limit)

    # Combine and format
    all_assessments = []

    for va in voice_assessments:
        all_assessments.append({
            "type": "voice",
            "assessment_id": va["assessment_id"],
            "date": va["assessed_at"],
            "cognitive_score": va["cognitive_score"],
            "mci_probability": va["mci_probability"],
            "flag": va["flag"],
            "details": dict(va)
        })

    for ma in mri_assessments:
        all_assessments.append({
            "type": "mri",
            "assessment_id": ma["assessment_id"],
            "date": ma["scan_date"] or ma["processed_at"],
            "classification": ma["classification"],
            "confidence": ma["confidence"],
            "details": dict(ma)
        })

    # Sort by date descending
    all_assessments.sort(key=lambda x: x["date"], reverse=True)

    return {"assessments": all_assessments[:limit]}


# ============================================================================
# Diagnoses
# ============================================================================
@router.get("/diagnoses", response_model=List[DiagnosisOut])
async def list_diagnoses(patient_id: int = Query(...)):
    """
    List all diagnoses for the patient.
    DEPRECATED: diagnoses table removed in 004 schema.
    Returns empty list for compatibility.
    """
    return []


# ============================================================================
# Profile Management
# ============================================================================
@router.get("/profile", response_model=PatientOut)
async def get_profile(patient_id: int = Query(...)):
    """Get patient profile with user information."""
    row = await db.fetchrow("""
        SELECT p.*, u.name, u.email, u.profile_image_url
        FROM patients p
        JOIN users u ON p.user_id = u.user_id
        WHERE p.user_id = $1
    """, patient_id)

    if not row:
        raise HTTPException(status_code=404, detail="Patient not found")

    return dict(row)


@router.put("/profile", response_model=PatientOut)
async def update_profile(patient_id: int = Query(...), payload: PatientUpdate = None):
    """
    Update patient profile.
    Only allows updating: emergency_contact, emergency_phone, notes.
    MCI stage can only be updated by doctors.
    """
    if not payload:
        raise HTTPException(status_code=400, detail="No update data provided")

    # Build update query
    updates = []
    values = []
    param_count = 1

    if payload.emergency_contact is not None:
        updates.append(f"emergency_contact = ${param_count}")
        values.append(payload.emergency_contact)
        param_count += 1

    if payload.emergency_phone is not None:
        updates.append(f"emergency_phone = ${param_count}")
        values.append(payload.emergency_phone)
        param_count += 1

    if payload.notes is not None:
        updates.append(f"notes = ${param_count}")
        values.append(payload.notes)
        param_count += 1

    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    # Add updated_at
    updates.append(f"updated_at = ${param_count}")
    values.append(_kst_now_naive())
    param_count += 1

    # Add patient_id for WHERE clause
    values.append(patient_id)

    query = f"""
        UPDATE patients
        SET {', '.join(updates)}
        WHERE user_id = ${param_count}
        RETURNING *
    """

    row = await db.fetchrow(query, *values)

    if not row:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Get user info
    user = await db.fetchrow("SELECT * FROM users WHERE user_id = $1", row["user_id"])

    result = dict(row)
    result.update({
        "name": user["name"],
        "email": user["email"],
        "profile_image_url": user["profile_image_url"]
    })

    logger.info(f"Profile updated for patient {patient_id}")

    return result
