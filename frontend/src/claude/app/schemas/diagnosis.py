from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from uuid import UUID


class DiagnosisBase(BaseModel):
    mci_stage: str  # 'normal', 'early_mci', 'late_mci', 'mild_dementia', 'AD'
    confidence: str  # 'confirmed', 'suspected', 'uncertain'
    notes: Optional[str] = None
    follow_up_date: Optional[date] = None


class DiagnosisCreate(DiagnosisBase):
    patient_id: UUID
    doctor_id: UUID
    based_on_mri: Optional[UUID] = None
    based_on_voice: Optional[UUID] = None


class DiagnosisUpdate(BaseModel):
    mci_stage: Optional[str] = None
    confidence: Optional[str] = None
    notes: Optional[str] = None
    follow_up_date: Optional[date] = None


class DiagnosisOut(DiagnosisBase):
    id: UUID
    patient_id: UUID
    doctor_id: UUID
    based_on_mri: Optional[UUID] = None
    based_on_voice: Optional[UUID] = None
    diagnosis_date: datetime

    class Config:
        from_attributes = True
