from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationOut(BaseModel):
    notification_id: str
    user_id: int
    type: str
    title: str
    message: Optional[str] = None
    related_link: Optional[str] = None
    is_read: bool
    created_at: datetime


class NotificationCreate(BaseModel):
    user_id: int
    type: str
    title: str
    message: Optional[str] = None
    related_link: Optional[str] = None
