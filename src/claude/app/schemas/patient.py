from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from uuid import UUID


class PatientBase(BaseModel):
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None
    mci_stage: Optional[str] = None  # 'normal', 'early_mci', 'late_mci', 'mild_dementia'
    diagnosis_date: Optional[date] = None
    notes: Optional[str] = None


class PatientCreate(PatientBase):
    user_id: UUID
    assigned_doctor_id: Optional[UUID] = None


class PatientUpdate(BaseModel):
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None
    mci_stage: Optional[str] = None
    diagnosis_date: Optional[date] = None
    assigned_doctor_id: Optional[UUID] = None
    notes: Optional[str] = None


class PatientOut(PatientBase):
    id: UUID
    user_id: UUID
    assigned_doctor_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PatientWithUser(PatientOut):
    """Patient with user info embedded"""
    name: str
    email: str
    profile_picture: Optional[str] = None
