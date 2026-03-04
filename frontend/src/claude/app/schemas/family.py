from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class FamilyMemberBase(BaseModel):
    relationship: str  # 'spouse', 'child', 'sibling', etc.
    can_view_recordings: bool = False
    can_view_transcripts: bool = True
    can_view_scores: bool = True


class FamilyMemberCreate(FamilyMemberBase):
    user_id: UUID
    patient_id: UUID
    approved_by: Optional[UUID] = None


class FamilyMemberUpdate(BaseModel):
    relationship: Optional[str] = None
    can_view_recordings: Optional[bool] = None
    can_view_transcripts: Optional[bool] = None
    can_view_scores: Optional[bool] = None


class FamilyMemberOut(FamilyMemberBase):
    id: UUID
    user_id: UUID
    patient_id: UUID
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
