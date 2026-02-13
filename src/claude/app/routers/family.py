from typing import List

from fastapi import APIRouter, HTTPException, Query

from .. import db
from ..schemas.patient import PatientOut
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
@router.get("/patient", response_model=PatientOut)
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
        SELECT id, started_at, ended_at
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


@router.get("/patient/assessments")
async def get_patient_assessments(family_id: int = Query(...), limit: int = Query(50, le=100)):
    """
    List all assessments (voice + MRI) for the patient.
    Family members can view assessment results to monitor patient's condition.
    """
    patient_id = await verify_family_access(family_id)

    # Get voice assessments
    voice_assessments = await db.fetch("""
        SELECT va.*, r.recording_date
        FROM voice_assessments va
        JOIN recordings r ON va.recording_id = r.recording_id
        WHERE r.patient_id = $1
        ORDER BY va.created_at DESC
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
        all_assessments.append({
            "type": "voice",
            "assessment_id": va["assessment_id"],
            "date": va["recording_date"],
            "predicted_stage": va["predicted_stage"],
            "confidence": va["confidence_score"],
            "details": {
                "language_score": va.get("language_score"),
                "fluency_score": va.get("fluency_score"),
                "coherence_score": va.get("coherence_score"),
                "vocabulary_score": va.get("vocabulary_score")
            }
        })

    for ma in mri_assessments:
        all_assessments.append({
            "type": "mri",
            "assessment_id": ma["assessment_id"],
            "date": ma["scan_date"],
            "predicted_stage": ma["predicted_stage"],
            "confidence": ma["confidence_score"],
            "details": {
                "brain_volume": ma.get("brain_volume"),
                "hippocampal_volume": ma.get("hippocampal_volume"),
                "ventricle_volume": ma.get("ventricle_volume")
            }
        })

    # Sort by date descending
    all_assessments.sort(key=lambda x: x["date"], reverse=True)

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
        SELECT fm.*, u.name, u.email, u.profile_image_url, p.user_id as patient_id
        FROM caregiver fm
        JOIN users u ON fm.user_id = u.user_id
        JOIN patients p ON fm.patient_id = p.user_id
        WHERE fm.user_id = $1
    """, family_id)

    if not row:
        raise HTTPException(status_code=404, detail="Family member not found")

    return dict(row)
