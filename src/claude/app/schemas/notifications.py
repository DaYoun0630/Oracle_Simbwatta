from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: str
    user_id: str
    type: str
    title: str
    message: Optional[str] = None
    related_patient_id: Optional[str] = None
    related_type: Optional[str] = None
    related_id: Optional[str] = None
    is_read: bool
    created_at: datetime


class NotificationCreate(BaseModel):
    user_id: str
    type: str
    title: str
    message: Optional[str] = None
    related_patient_id: Optional[str] = None
    related_type: Optional[str] = None
    related_id: Optional[str] = None
