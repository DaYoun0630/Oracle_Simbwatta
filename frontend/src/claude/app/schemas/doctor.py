from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class DoctorBase(BaseModel):
    hospital: Optional[str] = None
    department: Optional[str] = None
    license_number: Optional[str] = None
    specialization: Optional[str] = None


class DoctorCreate(DoctorBase):
    user_id: UUID


class DoctorUpdate(DoctorBase):
    pass


class DoctorOut(DoctorBase):
    id: UUID
    user_id: UUID

    class Config:
        from_attributes = True
