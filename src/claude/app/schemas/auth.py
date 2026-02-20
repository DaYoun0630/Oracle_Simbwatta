from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    entity_id: Optional[str] = None


class GoogleUser(BaseModel):
    """User info from Google OAuth"""
    email: EmailStr
    name: str
    picture: Optional[str] = None
    oauth_provider_id: str


class SubjectLinkVerifyRequest(BaseModel):
    subject_link_code: str = Field(..., min_length=1, max_length=64)


class SubjectLinkVerifyResponse(BaseModel):
    valid: bool
    message: str
    linked_subject_name: Optional[str] = None


class SignupTermsPayload(BaseModel):
    agree_service: bool
    agree_privacy: bool
    agree_marketing: bool = False


class PasswordRegisterRequest(BaseModel):
    role_code: Literal[0, 1, 2]
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone_number: Optional[str] = Field(default=None, max_length=30)
    date_of_birth: str = Field(..., min_length=10, max_length=10)
    password: str = Field(..., min_length=8, max_length=128)
    gender: Optional[Literal["male", "female"]] = None
    relationship: Optional[str] = Field(default=None, max_length=50)
    relationship_detail: Optional[str] = Field(default=None, max_length=100)
    subject_link_code: Optional[str] = Field(default=None, max_length=64)
    department: Optional[str] = Field(default=None, max_length=50)
    license_number: Optional[str] = Field(default=None, max_length=50)
    hospital: Optional[str] = Field(default=None, max_length=100)
    hospital_number: Optional[str] = Field(default=None, max_length=30)
    terms: Optional[SignupTermsPayload] = None


class PasswordLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class AuthUserPayload(BaseModel):
    id: int
    email: Optional[str] = None
    name: Optional[str] = None
    role: str
    entity_id: Optional[int] = None
    profile_image_url: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    department: Optional[str] = None
    license_number: Optional[str] = None
    hospital: Optional[str] = None
    hospital_number: Optional[str] = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserPayload
