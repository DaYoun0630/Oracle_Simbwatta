from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class RecordingBase(BaseModel):
    audio_path: str
    duration_seconds: Optional[float] = None
    file_size_bytes: Optional[int] = None
    format: Optional[str] = "wav"


class RecordingCreate(RecordingBase):
    patient_id: UUID
    session_id: Optional[UUID] = None


class RecordingUpdate(BaseModel):
    status: Optional[str] = None  # 'pending', 'processing', 'completed', 'failed'


class RecordingOut(RecordingBase):
    id: UUID
    patient_id: UUID
    session_id: Optional[UUID] = None
    recorded_at: datetime
    uploaded_at: datetime
    status: str

    class Config:
        from_attributes = True
