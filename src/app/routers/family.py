from datetime import date, datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, HTTPException, Query

from .. import db
from ..schemas.patient import PatientOut, PatientWithUser
from ..schemas.diagnosis import DiagnosisOut
from ..schemas.training import TrainingSessionOut
from ..schemas.family import FamilyMemberOut

router = APIRouter(prefix="/api/family", tags=["family"])


# ============================================================================
# Helper function to verify family access
# ============================================================================
async def verify_family_access(family_id: int) -> int:
    """
    Verify family member exists and return their patient_id.
    Raises HTTPException if not found.
    """
    row = await db.fetchrow("""
        SELECT patient_id FROM caregiver
        WHERE user_id = $1
    """, family_id)

    if not row:
        raise HTTPException(status_code=404, detail="Family member not found")

    return row["patient_id"]


# ============================================================================
# Patient Information (Read-Only)
# ============================================================================
@router.get("/patient", response_model=PatientWithUser)
async def get_patient(family_id: int = Query(...)):
    """
    Get patient information for the family member.
    Family members have read-only access to their assigned patient.
    """
    patient_id = await verify_family_access(family_id)

    # Get patient with user info
    row = await db.fetchrow("""
        SELECT p.*, u.name, u.email, u.profile_image_url
        FROM patients p
        JOIN users u ON p.user_id = u.user_id
        WHERE p.user_id = $1
    """, patient_id)

    if not row:
        raise HTTPException(status_code=404, detail="Patient not found")

    return dict(row)


@router.get("/patient/progress")
async def get_patient_progress(family_id: int = Query(...)):
    """
    Get patient's training progress and analytics.
    Read-only view for family members to monitor patient's activity.
    """
    patient_id = await verify_family_access(family_id)

    # Get session statistics
    sessions = await db.fetch("""
        SELECT
            COUNT(*) as total_sessions,
            COUNT(CASE WHEN ended_at IS NOT NULL THEN 1 END) as completed_sessions,
            SUM(EXTRACT(EPOCH FROM (ended_at - started_at))) / 3600.0 as total_hours
        FROM training_sessions
        WHERE patient_id = $1
    """, patient_id)

    # Get recent sessions
    recent_sessions = await db.fetch("""
        SELECT training_id AS id, started_at, ended_at
        FROM training_sessions
        WHERE patient_id = $1
        ORDER BY started_at DESC
        LIMIT 10
    """, patient_id)

    # Get assessment count
    assessment_stats = await db.fetchrow("""
        SELECT
            COUNT(DISTINCT va.assessment_id) as voice_assessments,
            COUNT(DISTINCT ma.assessment_id) as mri_assessments
        FROM patients p
        LEFT JOIN recordings r ON r.patient_id = p.user_id
        LEFT JOIN voice_assessments va ON va.recording_id = r.recording_id
        LEFT JOIN mri_assessments ma ON ma.patient_id = p.user_id
        WHERE p.user_id = $1
    """, patient_id)

    # Get patient's current stage
    patient = await db.fetchrow("SELECT risk_level FROM patients WHERE user_id = $1", patient_id)

    stats = dict(sessions[0]) if sessions else {}

    return {
        "patient_id": patient_id,
        "current_stage": patient.get("risk_level") or "unknown",
        "sessions": {
            "total": stats.get("total_sessions", 0),
            "completed": stats.get("completed_sessions", 0),
            "total_hours": round(stats.get("total_hours", 0.0), 2),
            "recent": [dict(s) for s in recent_sessions]
        },
        "assessments": {
            "voice": assessment_stats["voice_assessments"] or 0,
            "mri": assessment_stats["mri_assessments"] or 0
        }
    }

@router.get("/dashboard")
async def get_dashboard(family_id: int = Query(...)):
    """Dashboard data for the caregiver (alias for patient/progress)"""
    return await get_patient_progress(family_id)


@router.get("/weekly-trend")
async def get_weekly_trend(
    subjectId: str = Query(..., min_length=1),
    startDate: str = Query(..., min_length=10, max_length=10),
    endDate: str = Query(..., min_length=10, max_length=10),
):
    """Return daily voice-assessment trend points for caregiver dashboard."""
    try:
        start_date = datetime.strptime(startDate, "%Y-%m-%d").date()
        end_date = datetime.strptime(endDate, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="startDate/endDate must be YYYY-MM-DD") from exc

    if start_date > end_date:
        raise HTTPException(status_code=400, detail="startDate must be before or equal to endDate")

    patient = await db.fetchrow(
        """
        SELECT user_id
        FROM patients
        WHERE user_id::text = $1 OR subject_id = $1
        """,
        subjectId.strip(),
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient_id = int(patient["user_id"])
    rows = await db.fetch(
        """
        SELECT
            DATE(COALESCE(va.assessed_at, r.recorded_at, va.created_at)) AS day,
            AVG(va.cognitive_score) AS avg_score,
            AVG(COALESCE(va.confidence_score, 1.0 - va.mci_probability, 0.5)) AS avg_confidence,
            COUNT(*)::INT AS sample_count,
            BOOL_OR(COALESCE(va.flag, '') IN ('warning', 'critical')) AS has_anomaly
        FROM voice_assessments va
        JOIN recordings r ON r.recording_id = va.recording_id
        WHERE r.patient_id = $1
          AND DATE(COALESCE(va.assessed_at, r.recorded_at, va.created_at)) BETWEEN $2 AND $3
        GROUP BY day
        ORDER BY day
        """,
        patient_id,
        start_date,
        end_date,
    )

    by_day: Dict[date, dict] = {}
    for row in rows:
        row_dict = dict(row)
        day_value = row_dict["day"]
        if isinstance(day_value, datetime):
            day_key = day_value.date()
        else:
            day_key = day_value
        by_day[day_key] = row_dict

    points = []
    cursor = start_date
    valid_values: List[float] = []
    while cursor <= end_date:
        current = by_day.get(cursor)
        if not current or current.get("avg_score") is None:
            points.append(
                {
                    "date": cursor.isoformat(),
                    "value": None,
                    "sampleCount": 0,
                    "confidence": 0.0,
                    "flags": ["MISSING"],
                }
            )
        else:
            avg_score = float(current["avg_score"])
            avg_confidence = float(current.get("avg_confidence") or 0.5)
            has_anomaly = bool(current.get("has_anomaly"))
            sample_count = int(current.get("sample_count") or 0)
            flags = []
            if has_anomaly:
                flags.append("ANOMALY")
            if sample_count <= 1:
                flags.append("LOW_SAMPLE")
            points.append(
                {
                    "date": cursor.isoformat(),
                    "value": round(avg_score, 2),
                    "sampleCount": sample_count,
                    "confidence": round(max(0.0, min(1.0, avg_confidence)), 3),
                    "flags": flags,
                }
            )
            valid_values.append(avg_score)

        cursor += timedelta(days=1)

    latest_valid = next((point for point in reversed(points) if point["value"] is not None), None)
    if latest_valid is None:
        status_label = "유지 중"
        reason = "해당 기간의 음성 평가 데이터가 없어 추세를 계산할 수 없습니다."
        average_value = None
        delta_percent = None
    else:
        latest_has_anomaly = "ANOMALY" in latest_valid["flags"]
        if latest_has_anomaly:
            status_label = "관찰 필요"
            reason = "최근 음성 평가에서 변화 신호가 관찰되어 경과 확인이 필요합니다."
        else:
            status_label = "안정 흐름"
            reason = "최근 음성 평가 추세가 비교적 안정적으로 유지되고 있습니다."

        average_value = round(sum(valid_values) / len(valid_values), 2) if valid_values else None
        if valid_values and valid_values[0] != 0:
            delta_percent = round(((valid_values[-1] - valid_values[0]) / abs(valid_values[0])) * 100, 2)
        else:
            delta_percent = None

    return {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "points": points,
        "summary": {
            "statusLabel": status_label,
            "reason": reason,
            "avg": average_value,
            "deltaPercent": delta_percent,
        },
        "meta": {
            "source": "voice_assessments",
            "generatedAt": datetime.utcnow().isoformat() + "Z",
        },
    }


@router.get("/patient/assessments")
async def get_patient_assessments(family_id: int = Query(...), limit: int = Query(50, le=100)):
    """
    List all assessments (voice + MRI) for the patient.
    Family members can view assessment results to monitor patient's condition.
    """
    patient_id = await verify_family_access(family_id)

    # Get voice assessments
    voice_assessments = await db.fetch("""
        SELECT va.*, COALESCE(va.assessed_at, r.recorded_at, va.created_at) AS recording_date
        FROM voice_assessments va
        JOIN recordings r ON va.recording_id = r.recording_id
        WHERE r.patient_id = $1
        ORDER BY COALESCE(va.assessed_at, r.recorded_at, va.created_at) DESC
        LIMIT $2
    """, patient_id, limit)

    # Get MRI assessments
    mri_assessments = await db.fetch("""
        SELECT * FROM mri_assessments
        WHERE patient_id = $1
        ORDER BY created_at DESC
        LIMIT $2
    """, patient_id, limit)

    # Combine and format
    all_assessments = []

    for va in voice_assessments:
        va_dict = dict(va)
        all_assessments.append({
            "type": "voice",
            "assessment_id": va_dict["assessment_id"],
            "date": va_dict["recording_date"],
            "predicted_stage": va_dict.get("predicted_stage"),
            "confidence": va_dict.get("confidence_score"),
            "details": {
                "flag": va_dict.get("flag"),
                "cognitive_score": va_dict.get("cognitive_score"),
                "mci_probability": va_dict.get("mci_probability"),
                "language_score": va_dict.get("language_score"),
                "fluency_score": va_dict.get("fluency_score"),
                "coherence_score": va_dict.get("coherence_score"),
                "vocabulary_score": va_dict.get("vocabulary_score"),
            }
        })

    for ma in mri_assessments:
        ma_dict = dict(ma)
        all_assessments.append({
            "type": "mri",
            "assessment_id": ma_dict["assessment_id"],
            "date": ma_dict.get("scan_date"),
            "predicted_stage": ma_dict.get("predicted_stage"),
            "confidence": ma_dict.get("confidence"),
            "details": {
                "brain_volume": ma_dict.get("brain_volume"),
                "hippocampal_volume": ma_dict.get("hippocampal_volume"),
                "ventricle_volume": ma_dict.get("ventricle_volume"),
            }
        })

    # Sort by date descending
    all_assessments.sort(key=lambda x: x.get("date") or "", reverse=True)

    return {"assessments": all_assessments[:limit]}


@router.get("/patient/diagnoses", response_model=List[DiagnosisOut])
async def get_patient_diagnoses(family_id: int = Query(...)):
    # DEPRECATED
    return []


@router.get("/patient/sessions", response_model=List[TrainingSessionOut])
async def get_patient_sessions(family_id: int = Query(...), limit: int = Query(50, le=100)):
    """
    List patient's training sessions.
    Family members can monitor patient's chat activity and engagement.
    """
    patient_id = await verify_family_access(family_id)

    rows = await db.fetch("""
        SELECT * FROM training_sessions
        WHERE patient_id = $1
        ORDER BY started_at DESC
        LIMIT $2
    """, patient_id, limit)

    return [dict(r) for r in rows]


# ============================================================================
# Family Member Profile
# ============================================================================
@router.get("/profile", response_model=FamilyMemberOut)
async def get_profile(family_id: int = Query(...)):
    """
    Get family member profile with user information.
    Includes relationship to patient and notification preferences.
    """
    row = await db.fetchrow("""
        SELECT
            fm.user_id AS caregiver_id,
            fm.user_id,
            fm.patient_id,
            fm.relationship,
            fm.created_at
        FROM caregiver fm
        WHERE fm.user_id = $1
    """, family_id)

    if not row:
        raise HTTPException(status_code=404, detail="Family member not found")

    return dict(row)
