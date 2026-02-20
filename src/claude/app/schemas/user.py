from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: str  # 'doctor', 'patient', 'family'


class UserCreate(UserBase):
    oauth_provider_id: Optional[str] = None
    profile_image_url: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    profile_image_url: Optional[str] = None


class UserOut(UserBase):
    user_id: int
    oauth_provider_id: Optional[str] = None
    profile_image_url: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True
