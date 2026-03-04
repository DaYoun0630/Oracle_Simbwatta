from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


# Voice Assessment Schemas
class VoiceAssessmentBase(BaseModel):
    transcript: str
    cognitive_score: float  # 0-100
    mci_probability: float  # 0-1
    flag: str = "normal"  # 'normal', 'warning', 'critical'
    flag_reasons: Optional[List[str]] = None
    features: Optional[Dict[str, Any]] = None
    model_version: Optional[str] = None


class VoiceAssessmentCreate(VoiceAssessmentBase):
    recording_id: UUID


class VoiceAssessmentOut(VoiceAssessmentBase):
    assessment_id: UUID
    recording_id: UUID
    assessed_at: datetime
    shap_available: Optional[bool] = None
    shap_top_features: Optional[List[Dict[str, Any]]] = None
    shap_feature_contributions: Optional[List[Dict[str, Any]]] = None
    shap_meta: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# MRI Assessment Schemas
class MRIAssessmentBase(BaseModel):
    file_path: str
    classification: str  # 'CN', 'EMCI', 'LMCI', 'AD'
    probabilities: Dict[str, float]  # {"CN": 0.25, "EMCI": 0.21, ...}
    confidence: float
    model_version: Optional[str] = None


class MRIAssessmentCreate(MRIAssessmentBase):
    patient_id: int
    scan_date: Optional[datetime] = None


class MRIAssessmentOut(MRIAssessmentBase):
    assessment_id: UUID
    patient_id: int
    scan_date: Optional[datetime] = None
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
