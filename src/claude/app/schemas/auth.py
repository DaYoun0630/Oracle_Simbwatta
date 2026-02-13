from pydantic import BaseModel, EmailStr
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None


class GoogleUser(BaseModel):
    """User info from Google OAuth"""
    email: EmailStr
    name: str
    picture: Optional[str] = None
    oauth_provider_id: str
