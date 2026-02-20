from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class FamilyMemberBase(BaseModel):
    relationship: str  # 'spouse', 'child', 'sibling', etc.


class FamilyMemberCreate(FamilyMemberBase):
    user_id: int
    patient_id: int


class FamilyMemberUpdate(BaseModel):
    relationship: Optional[str] = None


class FamilyMemberOut(FamilyMemberBase):
    caregiver_id: int
    user_id: int
    patient_id: int
    created_at: datetime

    class Config:
        from_attributes = True
