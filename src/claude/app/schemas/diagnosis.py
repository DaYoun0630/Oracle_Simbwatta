from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from uuid import UUID

# DEPRECATED: diagnoses table removed in 004 schema
# Placeholder to prevent import errors
class DiagnosisBase(BaseModel):
    pass

class DiagnosisOut(BaseModel):
    pass
class DiagnosisCreate(BaseModel):
    pass
class DiagnosisUpdate(BaseModel):
    pass
