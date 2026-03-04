from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class Message(BaseModel):
    role: str  # 'system', 'user', 'assistant'
    content: str
    timestamp: Optional[datetime] = None


class TrainingSessionBase(BaseModel):
    exercise_type: str  # 'word_recall', 'story_retelling', 'daily_conversation'


class TrainingSessionCreate(TrainingSessionBase):
    patient_id: UUID


class TrainingSessionUpdate(BaseModel):
    ended_at: Optional[datetime] = None
    conversation: Optional[List[Dict[str, Any]]] = None


class TrainingSessionOut(TrainingSessionBase):
    id: UUID
    patient_id: UUID
    started_at: datetime
    ended_at: Optional[datetime] = None
    conversation: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True
