from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: str  # 'doctor', 'patient', 'family'


class UserCreate(UserBase):
    google_id: Optional[str] = None
    profile_picture: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    profile_picture: Optional[str] = None


class UserOut(UserBase):
    id: UUID
    google_id: Optional[str] = None
    profile_picture: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True
