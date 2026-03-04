from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class DoctorBase(BaseModel):
    hospital_name: Optional[str] = None
    hospital_number: Optional[str] = None
    license_number: Optional[str] = None


class DoctorCreate(DoctorBase):
    user_id: int


class DoctorUpdate(DoctorBase):
    pass


class DoctorOut(DoctorBase):
    user_id: int

    class Config:
        from_attributes = True
