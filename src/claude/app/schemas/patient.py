from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from uuid import UUID


class PatientBase(BaseModel):
    date_of_birth: Optional[date] = None
    gender: Optional[int] = None
    education_years: Optional[int] = None
    risk_level: Optional[str] = None
    rid: Optional[int] = None
    subject_id: Optional[str] = None


class PatientCreate(PatientBase):
    user_id: int
    doctor_id: Optional[int] = None


class PatientUpdate(BaseModel):
    date_of_birth: Optional[date] = None
    risk_level: Optional[str] = None
    doctor_id: Optional[int] = None
    notes: Optional[str] = None  # Note: notes might not be in patients table in 004, but keeping for now


class PatientOut(PatientBase):
    user_id: int
    doctor_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PatientWithUser(PatientOut):
    """Patient with user info embedded"""
    name: str
    email: str
    profile_image_url: Optional[str] = None
