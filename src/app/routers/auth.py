import base64
import hashlib
import hmac
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from uuid import uuid4

import asyncpg
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .. import db
from ..config import settings
from ..schemas.auth import (
    AuthResponse,
    AuthUserPayload,
    PasswordLoginRequest,
    PasswordRegisterRequest,
    ProfileUpdateRequest,
    SubjectLinkVerifyRequest,
    SubjectLinkVerifyResponse,
    TokenData,
    UserSettingsPayload,
    UserSettingsUpdateRequest,
)
from ..schemas.user import UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()
logger = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9))

PASSWORD_SCHEME = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 390_000
SUBJECT_LINK_PATTERN = re.compile(r"^SM-?(\d{1,6})$")
NUMERIC_LINK_PATTERN = re.compile(r"^(\d{1,6})$")
ROLE_CODE_TO_ROLE = {0: "patient", 1: "caregiver", 2: "doctor"}
MEMBER_CODE_MODULUS = 1_000_000
MEMBER_CODE_MULTIPLIER = 741_457
MEMBER_CODE_INCREMENT = 193_939
MEMBER_CODE_MULTIPLIER_INV = pow(MEMBER_CODE_MULTIPLIER, -1, MEMBER_CODE_MODULUS)
USER_SETTINGS_DEFAULTS: Dict[str, bool] = {
    "notify_emergency": True,
    "notify_weekly": True,
    "notify_service": True,
    "doctor_notify_risk": True,
    "doctor_notify_weekly": True,
    "doctor_notify_mri": True,
    "share_dialog_summary": True,
    "share_anomaly_alert": True,
    "share_medication_reminder": True,
}
USER_SETTINGS_COLUMNS = tuple(USER_SETTINGS_DEFAULTS.keys())
_user_settings_table_ready = False


def _kst_now_naive() -> datetime:
    """Return current Korea time as naive datetime for TIMESTAMP columns."""
    return datetime.now(KST).replace(tzinfo=None)


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _decode_member_code_to_user_id(encoded_number: int) -> Optional[int]:
    if encoded_number < 0:
        return None
    decoded = ((encoded_number - MEMBER_CODE_INCREMENT) * MEMBER_CODE_MULTIPLIER_INV) % MEMBER_CODE_MODULUS
    if decoded <= 0:
        return None
    return decoded


def _parse_date_of_birth(date_str: str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="date_of_birth must be YYYY-MM-DD") from exc


def _gender_to_smallint(gender: Optional[str]) -> Optional[int]:
    if gender is None:
        return None
    normalized = gender.strip().lower()
    if normalized == "female":
        return 0
    if normalized == "male":
        return 1
    return None


def _format_date_iso(value) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    salt_b64 = base64.urlsafe_b64encode(salt).decode("utf-8")
    digest_b64 = base64.urlsafe_b64encode(digest).decode("utf-8")
    return f"{PASSWORD_SCHEME}${PBKDF2_ITERATIONS}${salt_b64}${digest_b64}"


def _verify_password(password: str, encoded_hash: Optional[str]) -> bool:
    if not encoded_hash:
        return False

    parts = encoded_hash.split("$")
    if len(parts) != 4:
        return False

    scheme, iterations_str, salt_b64, digest_b64 = parts
    if scheme != PASSWORD_SCHEME:
        return False

    try:
        iterations = int(iterations_str)
        salt = base64.urlsafe_b64decode(salt_b64.encode("utf-8"))
        expected_digest = base64.urlsafe_b64decode(digest_b64.encode("utf-8"))
    except Exception:
        return False

    computed_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(computed_digest, expected_digest)


async def _resolve_role_for_user(user_id: int) -> Tuple[str, int]:
    if await db.fetchrow("SELECT user_id FROM doctor WHERE user_id = $1", user_id):
        return "doctor", user_id
    if await db.fetchrow("SELECT user_id FROM caregiver WHERE user_id = $1", user_id):
        return "caregiver", user_id
    return "patient", user_id


async def _resolve_subject_link_code(
    subject_link_code: str,
    conn: Optional[asyncpg.Connection] = None,
) -> Tuple[int, str]:
    async def fetchrow(query: str, *args):
        if conn is not None:
            return await conn.fetchrow(query, *args)
        return await db.fetchrow(query, *args)

    raw_code = subject_link_code.strip()
    if not raw_code:
        raise HTTPException(status_code=400, detail="subject_link_code is required")

    normalized = re.sub(r"\s+", "", raw_code).upper()
    patient = None
    candidate_patient_ids = []

    code_match = SUBJECT_LINK_PATTERN.match(normalized)
    if code_match:
        encoded = int(code_match.group(1))
        decoded_patient_id = _decode_member_code_to_user_id(encoded)
        if decoded_patient_id is not None:
            candidate_patient_ids.append(decoded_patient_id)
        # Backward compatibility: legacy UI used SM-{zero-padded user_id}.
        if encoded not in candidate_patient_ids:
            candidate_patient_ids.append(encoded)
    else:
        numeric_match = NUMERIC_LINK_PATTERN.match(normalized)
        if numeric_match:
            candidate_patient_ids.append(int(numeric_match.group(1)))

    for candidate_patient_id in candidate_patient_ids:
        patient = await fetchrow(
            """
            SELECT p.user_id, COALESCE(u.name, '') AS patient_name
            FROM patients p
            JOIN users u ON u.user_id = p.user_id
            WHERE p.user_id = $1
            """,
            candidate_patient_id,
        )
        if patient:
            break

    if not patient:
        patient = await fetchrow(
            """
            SELECT p.user_id, COALESCE(u.name, '') AS patient_name
            FROM patients p
            JOIN users u ON u.user_id = p.user_id
            WHERE UPPER(COALESCE(p.subject_id, '')) = $1
            """,
            normalized,
        )

    if not patient:
        raise HTTPException(status_code=400, detail="유효하지 않은 대상자 회원번호입니다.")

    patient_name = patient["patient_name"] or "대상자"
    return int(patient["user_id"]), patient_name


def _build_auth_response(
    *,
    user_id: int,
    email: Optional[str],
    name: Optional[str],
    role: str,
    entity_id: int,
    profile_image_url: Optional[str],
    access_token: str,
    phone_number: Optional[str] = None,
    date_of_birth: Optional[str] = None,
    department: Optional[str] = None,
    license_number: Optional[str] = None,
    hospital: Optional[str] = None,
    hospital_number: Optional[str] = None,
):
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": email,
            "name": name,
            "role": role,
            "entity_id": entity_id,
            "profile_image_url": profile_image_url,
            "phone_number": phone_number,
            "date_of_birth": date_of_birth,
            "department": department,
            "license_number": license_number,
            "hospital": hospital,
            "hospital_number": hospital_number,
        },
    }


async def _fetch_auth_user_payload(user_id: int) -> dict:
    user = await db.fetchrow(
        """
        SELECT
            u.user_id,
            u.email,
            u.name,
            u.profile_image_url,
            u.phone_number,
            u.date_of_birth,
            d.department,
            d.license_number,
            d.hospital,
            d.hospital_number
        FROM users u
        LEFT JOIN doctor d ON d.user_id = u.user_id
        WHERE u.user_id = $1
        LIMIT 1
        """,
        user_id,
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role, entity_id = await _resolve_role_for_user(user_id)
    return {
        "id": int(user["user_id"]),
        "email": user.get("email"),
        "name": user.get("name"),
        "role": role,
        "entity_id": entity_id,
        "profile_image_url": user.get("profile_image_url"),
        "phone_number": user.get("phone_number"),
        "date_of_birth": _format_date_iso(user.get("date_of_birth")),
        "department": user.get("department"),
        "license_number": user.get("license_number"),
        "hospital": user.get("hospital"),
        "hospital_number": user.get("hospital_number"),
    }


async def _ensure_user_settings_table() -> None:
    global _user_settings_table_ready
    if _user_settings_table_ready:
        return

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            notify_emergency BOOLEAN NOT NULL DEFAULT TRUE,
            notify_weekly BOOLEAN NOT NULL DEFAULT TRUE,
            notify_service BOOLEAN NOT NULL DEFAULT TRUE,
            doctor_notify_risk BOOLEAN NOT NULL DEFAULT TRUE,
            doctor_notify_weekly BOOLEAN NOT NULL DEFAULT TRUE,
            doctor_notify_mri BOOLEAN NOT NULL DEFAULT TRUE,
            share_dialog_summary BOOLEAN NOT NULL DEFAULT TRUE,
            share_anomaly_alert BOOLEAN NOT NULL DEFAULT TRUE,
            share_medication_reminder BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    _user_settings_table_ready = True


def _settings_row_to_payload(row) -> dict:
    payload = {}
    for column in USER_SETTINGS_COLUMNS:
        if row:
            payload[column] = bool(row.get(column))
        else:
            payload[column] = bool(USER_SETTINGS_DEFAULTS[column])
    return payload


async def _get_or_create_user_settings(user_id: int):
    await _ensure_user_settings_table()

    row = await db.fetchrow(
        f"""
        SELECT {", ".join(USER_SETTINGS_COLUMNS)}
        FROM user_settings
        WHERE user_id = $1
        """,
        user_id,
    )
    if row:
        return row

    now = _kst_now_naive()
    row = await db.fetchrow(
        f"""
        INSERT INTO user_settings (
            user_id,
            {", ".join(USER_SETTINGS_COLUMNS)},
            created_at,
            updated_at
        )
        VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
            $11, $12
        )
        ON CONFLICT (user_id) DO UPDATE
        SET updated_at = EXCLUDED.updated_at
        RETURNING {", ".join(USER_SETTINGS_COLUMNS)}
        """,
        user_id,
        USER_SETTINGS_DEFAULTS["notify_emergency"],
        USER_SETTINGS_DEFAULTS["notify_weekly"],
        USER_SETTINGS_DEFAULTS["notify_service"],
        USER_SETTINGS_DEFAULTS["doctor_notify_risk"],
        USER_SETTINGS_DEFAULTS["doctor_notify_weekly"],
        USER_SETTINGS_DEFAULTS["doctor_notify_mri"],
        USER_SETTINGS_DEFAULTS["share_dialog_summary"],
        USER_SETTINGS_DEFAULTS["share_anomaly_alert"],
        USER_SETTINGS_DEFAULTS["share_medication_reminder"],
        now,
        now,
    )
    return row


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
        user_id: Optional[str] = payload.get("sub")
        role: Optional[str] = payload.get("role")
        entity_id: Optional[str] = payload.get("entity_id")
        email: Optional[str] = payload.get("email")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        return TokenData(user_id=user_id, role=role, entity_id=entity_id, email=email)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Dependency to get current authenticated user from JWT token."""
    token = credentials.credentials
    return verify_token(token)


# ============================================================================
# Password Auth
# ============================================================================
@router.post("/verify-subject-link", response_model=SubjectLinkVerifyResponse)
async def verify_subject_link(payload: SubjectLinkVerifyRequest):
    try:
        _, patient_name = await _resolve_subject_link_code(payload.subject_link_code)
    except HTTPException as exc:
        return {
            "valid": False,
            "message": str(exc.detail),
            "linked_subject_name": None,
        }

    return {
        "valid": True,
        "message": f"연결 가능한 대상자: {patient_name}",
        "linked_subject_name": patient_name,
    }


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register_with_password(payload: PasswordRegisterRequest):
    if not payload.terms or not payload.terms.agree_service or not payload.terms.agree_privacy:
        raise HTTPException(status_code=400, detail="필수 약관 동의가 필요합니다.")

    role = ROLE_CODE_TO_ROLE[payload.role_code]
    now = _kst_now_naive()
    date_of_birth = _parse_date_of_birth(payload.date_of_birth)
    password_hash = _hash_password(payload.password)
    normalized_email = payload.email.strip().lower()
    phone_number = _normalize_optional_text(payload.phone_number)
    doctor_department = None
    doctor_license_number = None
    doctor_hospital = None
    doctor_hospital_number = None

    pool = db.get_pool()
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                existing_user = await conn.fetchrow(
                    "SELECT user_id FROM users WHERE lower(email) = lower($1)",
                    normalized_email,
                )
                if existing_user:
                    raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다.")

                created_user = await conn.fetchrow(
                    """
                    INSERT INTO users (
                        name,
                        phone_number,
                        email,
                        date_of_birth,
                        password_hash,
                        created_at,
                        updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING user_id, email, name, profile_image_url
                    """,
                    payload.name.strip(),
                    phone_number,
                    normalized_email,
                    date_of_birth,
                    password_hash,
                    now,
                    now,
                )
                user_id = int(created_user["user_id"])

                if role == "patient":
                    await conn.execute(
                        """
                        INSERT INTO patients (
                            user_id,
                            enrollment_date,
                            gender,
                            date_of_birth,
                            created_at,
                            updated_at
                        )
                        VALUES ($1, CURRENT_DATE, $2, $3, $4, $5)
                        """,
                        user_id,
                        _gender_to_smallint(payload.gender),
                        date_of_birth,
                        now,
                        now,
                    )
                    entity_id = user_id
                elif role == "caregiver":
                    if not payload.subject_link_code:
                        raise HTTPException(status_code=400, detail="subject_link_code is required")

                    patient_id, _ = await _resolve_subject_link_code(payload.subject_link_code, conn)
                    relationship = _normalize_optional_text(payload.relationship)
                    relationship_detail = _normalize_optional_text(payload.relationship_detail)
                    if relationship == "other" and relationship_detail:
                        relationship = relationship_detail
                    if not relationship:
                        raise HTTPException(status_code=400, detail="relationship is required")

                    await conn.execute(
                        """
                        INSERT INTO caregiver (user_id, patient_id, relationship, created_at)
                        VALUES ($1, $2, $3, $4)
                        """,
                        user_id,
                        patient_id,
                        relationship,
                        now,
                    )
                    entity_id = user_id
                else:
                    department = _normalize_optional_text(payload.department)
                    license_number = _normalize_optional_text(payload.license_number)
                    hospital = _normalize_optional_text(payload.hospital)
                    hospital_number = _normalize_optional_text(payload.hospital_number)
                    if not department or not license_number or not hospital or not hospital_number:
                        raise HTTPException(
                            status_code=400,
                            detail="doctor role requires department, license_number, hospital, hospital_number",
                        )

                    await conn.execute(
                        """
                        INSERT INTO doctor (
                            user_id,
                            department,
                            license_number,
                            hospital,
                            hospital_number,
                            created_at
                        )
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        user_id,
                        department,
                        license_number,
                        hospital,
                        hospital_number,
                        now,
                    )
                    doctor_department = department
                    doctor_license_number = license_number
                    doctor_hospital = hospital
                    doctor_hospital_number = hospital_number
                    entity_id = user_id
    except asyncpg.UndefinedColumnError as exc:
        message = str(exc)
        if "password_hash" in message:
            raise HTTPException(
                status_code=500,
                detail="password_hash column is missing. Apply migrations/009_add_password_hash_to_users.sql first.",
            ) from exc
        raise

    token_data = {
        "sub": str(user_id),
        "role": role,
        "entity_id": str(entity_id),
        "email": normalized_email,
    }
    access_token = create_access_token(token_data)

    logger.info("User registered: %s (%s)", user_id, role)
    return _build_auth_response(
        user_id=user_id,
        email=normalized_email,
        name=payload.name.strip(),
        role=role,
        entity_id=entity_id,
        profile_image_url=None,
        phone_number=phone_number,
        date_of_birth=_format_date_iso(date_of_birth),
        department=doctor_department,
        license_number=doctor_license_number,
        hospital=doctor_hospital,
        hospital_number=doctor_hospital_number,
        access_token=access_token,
    )


@router.post("/login", response_model=AuthResponse)
async def login_with_password(payload: PasswordLoginRequest):
    try:
        user = await db.fetchrow(
            """
            SELECT
                u.user_id,
                u.email,
                u.name,
                u.profile_image_url,
                u.password_hash,
                u.phone_number,
                u.date_of_birth,
                d.department,
                d.license_number,
                d.hospital,
                d.hospital_number
            FROM users u
            LEFT JOIN doctor d ON d.user_id = u.user_id
            WHERE lower(u.email) = lower($1)
            LIMIT 1
            """,
            payload.email.strip(),
        )
    except asyncpg.UndefinedColumnError as exc:
        raise HTTPException(
            status_code=500,
            detail="password_hash column is missing. Apply migrations/009_add_password_hash_to_users.sql first.",
        ) from exc

    if not user or not _verify_password(payload.password, user.get("password_hash")):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    user_id = int(user["user_id"])
    role, entity_id = await _resolve_role_for_user(user_id)

    token_data = {
        "sub": str(user_id),
        "role": role,
        "entity_id": str(entity_id),
        "email": user["email"],
    }
    access_token = create_access_token(token_data)
    logger.info("User logged in with password: %s (%s)", user_id, role)

    return _build_auth_response(
        user_id=user_id,
        email=user["email"],
        name=user["name"],
        role=role,
        entity_id=entity_id,
        profile_image_url=user["profile_image_url"],
        phone_number=user.get("phone_number"),
        date_of_birth=_format_date_iso(user.get("date_of_birth")),
        department=user.get("department"),
        license_number=user.get("license_number"),
        hospital=user.get("hospital"),
        hospital_number=user.get("hospital_number"),
        access_token=access_token,
    )


# ============================================================================
# Development Login (No OAuth required)
# ============================================================================
@router.post("/dev-login")
async def dev_login(role: str = Query("doctor", pattern="^(doctor|patient|caregiver)$")):
    """
    Development only: Get a JWT token for a specific role without Google OAuth.
    Creates a mock user if one doesn't exist for the role.
    """
    if settings.environment == "production":
        raise HTTPException(status_code=403, detail="Not available in production")

    email = f"dev_{role}@example.com"
    user = await db.fetchrow("SELECT * FROM users WHERE email = $1", email)

    if not user:
        now = _kst_now_naive()
        row = await db.fetchrow(
            """
            INSERT INTO users (email, name, oauth_provider_id, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING user_id
            """,
            email,
            f"Dev {role.capitalize()}",
            "dev-mock-id",
            now,
            now,
        )
        user_id = int(row["user_id"])

        if role == "doctor":
            await db.execute("INSERT INTO doctor (user_id) VALUES ($1)", user_id)
        elif role == "patient":
            await db.execute("INSERT INTO patients (user_id, enrollment_date) VALUES ($1, CURRENT_DATE)", user_id)
    else:
        user_id = int(user["user_id"])

    token_data = {"sub": str(user_id), "role": role, "email": email}
    access_token = create_access_token(token_data)
    return {"access_token": access_token, "token_type": "bearer", "role": role}


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
    state = uuid4().hex
    if redirect_uri:
        # TODO: Store state -> redirect_uri mapping in Redis with TTL
        pass

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

    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=token_data)
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get access token from Google")

        tokens = token_response.json()
        access_token = tokens.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token in response")

        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        userinfo_response = await client.get(userinfo_url, headers=headers)
        if userinfo_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")

        google_user = userinfo_response.json()

    google_id = google_user.get("id")
    email = google_user.get("email")
    name = google_user.get("name")
    picture = google_user.get("picture")
    if not google_id or not email:
        raise HTTPException(status_code=400, detail="Invalid user data from Google")

    user = await db.fetchrow("SELECT * FROM users WHERE oauth_provider_id = $1", google_id)
    now = _kst_now_naive()
    if user:
        user_id = int(user["user_id"])
        await db.execute(
            """
            UPDATE users
            SET name = $1, email = $2, profile_image_url = $3, updated_at = $4
            WHERE user_id = $5
            """,
            name,
            email,
            picture,
            now,
            user_id,
        )
    else:
        row = await db.fetchrow(
            """
            INSERT INTO users (oauth_provider_id, email, name, profile_image_url, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING user_id
            """,
            google_id,
            email,
            name,
            picture,
            now,
            now,
        )
        user_id = int(row["user_id"])
        await db.execute(
            """
            INSERT INTO patients (user_id, enrollment_date, created_at, updated_at)
            VALUES ($1, CURRENT_DATE, $2, $3)
            """,
            user_id,
            now,
            now,
        )

    role, entity_id = await _resolve_role_for_user(user_id)
    token_payload = {
        "sub": str(user_id),
        "role": role,
        "entity_id": str(entity_id),
        "email": email,
    }
    jwt_token = create_access_token(token_payload)
    logger.info("User logged in: %s (%s)", user_id, role)

    return _build_auth_response(
        user_id=user_id,
        email=email,
        name=name,
        role=role,
        entity_id=entity_id,
        profile_image_url=picture,
        phone_number=None,
        date_of_birth=None,
        department=None,
        license_number=None,
        hospital=None,
        hospital_number=None,
        access_token=jwt_token,
    )


# ============================================================================
# Profile & Settings
# ============================================================================
@router.get("/profile", response_model=AuthUserPayload)
async def get_auth_profile(current_user: TokenData = Depends(get_current_user)):
    return await _fetch_auth_user_payload(int(current_user.user_id))


@router.put("/profile", response_model=AuthUserPayload)
async def update_auth_profile(
    payload: ProfileUpdateRequest,
    current_user: TokenData = Depends(get_current_user),
):
    user_id = int(current_user.user_id)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return await _fetch_auth_user_payload(user_id)

    now = _kst_now_naive()
    role, _ = await _resolve_role_for_user(user_id)

    user_updates = {}
    if "name" in updates:
        user_updates["name"] = _normalize_optional_text(updates["name"])
    if "phone_number" in updates:
        user_updates["phone_number"] = _normalize_optional_text(updates["phone_number"])
    if "profile_image_url" in updates:
        user_updates["profile_image_url"] = _normalize_optional_text(updates["profile_image_url"])
    if "date_of_birth" in updates:
        date_of_birth_raw = updates["date_of_birth"]
        if date_of_birth_raw is None:
            user_updates["date_of_birth"] = None
        else:
            normalized_dob = str(date_of_birth_raw).strip()
            user_updates["date_of_birth"] = _parse_date_of_birth(normalized_dob) if normalized_dob else None

    if user_updates:
        columns = tuple(user_updates.keys())
        values = [user_updates[column] for column in columns]
        set_parts = [f"{column} = ${index + 1}" for index, column in enumerate(columns)]
        values.append(now)
        set_parts.append(f"updated_at = ${len(values)}")
        values.append(user_id)
        await db.execute(
            f"""
            UPDATE users
            SET {", ".join(set_parts)}
            WHERE user_id = ${len(values)}
            """,
            *values,
        )

    doctor_update_fields = ("department", "license_number", "hospital", "hospital_number")
    doctor_updates = {}
    for field in doctor_update_fields:
        if field in updates:
            doctor_updates[field] = _normalize_optional_text(updates[field])

    if doctor_updates:
        if role != "doctor":
            raise HTTPException(status_code=403, detail="Doctor profile fields are only available to doctor users.")

        await db.execute(
            """
            INSERT INTO doctor (user_id, created_at)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id,
            now,
        )
        columns = tuple(doctor_updates.keys())
        values = [doctor_updates[column] for column in columns]
        set_parts = [f"{column} = ${index + 1}" for index, column in enumerate(columns)]
        values.append(user_id)
        await db.execute(
            f"""
            UPDATE doctor
            SET {", ".join(set_parts)}
            WHERE user_id = ${len(values)}
            """,
            *values,
        )

    return await _fetch_auth_user_payload(user_id)


@router.get("/settings", response_model=UserSettingsPayload)
async def get_user_settings(current_user: TokenData = Depends(get_current_user)):
    row = await _get_or_create_user_settings(int(current_user.user_id))
    return _settings_row_to_payload(row)


@router.put("/settings", response_model=UserSettingsPayload)
async def update_user_settings(
    payload: UserSettingsUpdateRequest,
    current_user: TokenData = Depends(get_current_user),
):
    user_id = int(current_user.user_id)
    updates = payload.model_dump(exclude_unset=True)
    current = _settings_row_to_payload(await _get_or_create_user_settings(user_id))
    current.update({key: bool(value) for key, value in updates.items()})

    now = _kst_now_naive()
    row = await db.fetchrow(
        f"""
        INSERT INTO user_settings (
            user_id,
            {", ".join(USER_SETTINGS_COLUMNS)},
            created_at,
            updated_at
        )
        VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
            $11, $12
        )
        ON CONFLICT (user_id) DO UPDATE
        SET
            notify_emergency = EXCLUDED.notify_emergency,
            notify_weekly = EXCLUDED.notify_weekly,
            notify_service = EXCLUDED.notify_service,
            doctor_notify_risk = EXCLUDED.doctor_notify_risk,
            doctor_notify_weekly = EXCLUDED.doctor_notify_weekly,
            doctor_notify_mri = EXCLUDED.doctor_notify_mri,
            share_dialog_summary = EXCLUDED.share_dialog_summary,
            share_anomaly_alert = EXCLUDED.share_anomaly_alert,
            share_medication_reminder = EXCLUDED.share_medication_reminder,
            updated_at = EXCLUDED.updated_at
        RETURNING {", ".join(USER_SETTINGS_COLUMNS)}
        """,
        user_id,
        current["notify_emergency"],
        current["notify_weekly"],
        current["notify_service"],
        current["doctor_notify_risk"],
        current["doctor_notify_weekly"],
        current["doctor_notify_mri"],
        current["share_dialog_summary"],
        current["share_anomaly_alert"],
        current["share_medication_reminder"],
        now,
        now,
    )
    return _settings_row_to_payload(row)


# ============================================================================
# User Info
# ============================================================================
@router.get("/me", response_model=UserOut)
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """
    Get current authenticated user's information.
    Requires valid JWT token in Authorization header.
    """
    user = await db.fetchrow("SELECT * FROM users WHERE user_id = $1", int(current_user.user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role, entity_id = await _resolve_role_for_user(int(user["user_id"]))
    payload = dict(user)
    payload["role"] = role
    payload["entity_id"] = entity_id
    return payload


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
    logger.info("User logged out: %s", current_user.user_id)
    return {"status": "ok", "message": "Logged out successfully"}
