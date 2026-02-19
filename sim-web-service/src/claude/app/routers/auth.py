from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import httpx

from .. import db
from ..config import settings
from ..schemas.auth import Token, TokenData, GoogleUser
from ..schemas.user import UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()


# ============================================================================
# JWT Token Management
# ============================================================================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        entity_id: str = payload.get("entity_id")  # doctor_id, patient_id, or family_id

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        return TokenData(user_id=user_id, role=role, entity_id=entity_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Dependency to get current authenticated user from JWT token."""
    token = credentials.credentials
    return verify_token(token)


# ============================================================================
# Google OAuth Flow
# ============================================================================
@router.get("/google")
async def google_oauth_start(redirect_uri: str = Query(None)):
    """
    Start Google OAuth flow.
    Redirects user to Google's OAuth consent screen.

    Query params:
    - redirect_uri: Optional URL to redirect to after successful authentication
    """
    # Store redirect_uri in state parameter for callback
    state = uuid4().hex
    if redirect_uri:
        # TODO: Store state -> redirect_uri mapping in Redis with TTL
        pass

    # Build Google OAuth URL
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.google_client_id}&"
        f"redirect_uri={settings.google_redirect_uri}&"
        f"response_type=code&"
        f"scope=openid email profile&"
        f"state={state}&"
        f"access_type=offline&"
        f"prompt=consent"
    )

    return RedirectResponse(url=google_auth_url)


@router.get("/google/callback")
async def google_oauth_callback(code: str = Query(...), state: str = Query(None)):
    """
    Handle Google OAuth callback.
    Exchanges authorization code for access token and user info.
    Creates or updates user in database and returns JWT token.
    """
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code missing")

    # Exchange code for access token
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code"
    }

    async with httpx.AsyncClient() as client:
        # Get access token
        token_response = await client.post(token_url, data=token_data)
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get access token from Google")

        tokens = token_response.json()
        access_token = tokens.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="No access token in response")

        # Get user info
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        userinfo_response = await client.get(userinfo_url, headers=headers)

        if userinfo_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")

        google_user = userinfo_response.json()

    # Extract user data
    google_id = google_user.get("id")
    email = google_user.get("email")
    name = google_user.get("name")
    picture = google_user.get("picture")

    if not google_id or not email:
        raise HTTPException(status_code=400, detail="Invalid user data from Google")

    # Check if user exists
    user = await db.fetchrow("SELECT * FROM users WHERE google_id = $1", google_id)

    now = datetime.utcnow()
    if user:
        # Update existing user
        user_id = user["id"]
        await db.execute("""
            UPDATE users
            SET name = $1, email = $2, profile_picture = $3, updated_at = $4
            WHERE id = $5
        """, name, email, picture, now, user_id)
    else:
        # Create new user (default role: patient)
        user_id = str(uuid4())
        await db.execute("""
            INSERT INTO users (id, google_id, email, name, role, profile_picture, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, user_id, google_id, email, name, "patient", picture, now, now)

        # Create patient record
        patient_id = str(uuid4())
        await db.execute("""
            INSERT INTO patients (id, user_id, mci_stage, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5)
        """, patient_id, user_id, "unknown", now, now)

    # Get user role and entity_id
    user = await db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    role = user["role"]

    # Get entity_id based on role
    entity_id = None
    if role == "doctor":
        doctor = await db.fetchrow("SELECT id FROM doctors WHERE user_id = $1", user_id)
        entity_id = doctor["id"] if doctor else None
    elif role == "patient":
        patient = await db.fetchrow("SELECT id FROM patients WHERE user_id = $1", user_id)
        entity_id = patient["id"] if patient else None
    elif role == "family":
        family = await db.fetchrow("SELECT id FROM family_members WHERE user_id = $1", user_id)
        entity_id = family["id"] if family else None

    # Create JWT token
    token_data = {
        "sub": user_id,
        "role": role,
        "entity_id": entity_id,
        "email": email
    }
    access_token = create_access_token(token_data)

    # Log successful login
    await db.execute("""
        INSERT INTO audit_logs (id, user_id, action, details, created_at)
        VALUES ($1, $2, $3, $4, $5)
    """, str(uuid4()), user_id, "login", {"method": "google_oauth"}, now)

    # TODO: Retrieve redirect_uri from state if stored in Redis
    # For now, return token directly
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": email,
            "name": name,
            "role": role,
            "entity_id": entity_id,
            "profile_picture": picture
        }
    }


# ============================================================================
# User Info
# ============================================================================
@router.get("/me", response_model=UserOut)
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """
    Get current authenticated user's information.
    Requires valid JWT token in Authorization header.
    """
    user = await db.fetchrow("SELECT * FROM users WHERE id = $1", current_user.user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return dict(user)


# ============================================================================
# Logout
# ============================================================================
@router.post("/logout")
async def logout(current_user: TokenData = Depends(get_current_user)):
    """
    Logout current user.
    Client should delete the JWT token.
    TODO: Add token to blacklist in Redis if needed.
    """
    # Log logout
    await db.execute("""
        INSERT INTO audit_logs (id, user_id, action, details, created_at)
        VALUES ($1, $2, $3, $4, $5)
    """, str(uuid4()), current_user.user_id, "logout", {}, datetime.utcnow())

    return {"status": "ok", "message": "Logged out successfully"}
