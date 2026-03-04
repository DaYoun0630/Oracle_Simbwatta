from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from uuid import UUID

from .. import db
from ..schemas.patient import PatientOut, PatientCreate, PatientUpdate, PatientWithUser
from ..schemas.recording import RecordingOut
from ..schemas.assessment import VoiceAssessmentOut, MRIAssessmentOut
from ..schemas.diagnosis import DiagnosisOut, DiagnosisCreate, DiagnosisUpdate
from ..schemas.family import FamilyMemberOut, FamilyMemberCreate

router = APIRouter(prefix="/api/doctor", tags=["doctor"])


# TODO: Add auth dependency to verify user is a doctor
# from ..auth.dependencies import get_current_doctor

@router.get("/patients", response_model=List[PatientWithUser])
async def list_patients(
    doctor_id: str = Query(..., description="Doctor ID for filtering")
):
    """List all patients assigned to this doctor"""
    rows = await db.fetch(
        """
        SELECT p.*, u.name, u.email, u.profile_picture
        FROM patients p
        JOIN users u ON p.user_id = u.id
        WHERE p.assigned_doctor_id = $1
        ORDER BY p.created_at DESC
        """,
        doctor_id
    )
    return [dict(r) for r in rows]


@router.get("/patients/{patient_id}", response_model=PatientWithUser)
async def get_patient(patient_id: UUID):
    """Get detailed patient information"""
    row = await db.fetchrow(
        """
        SELECT p.*, u.name, u.email, u.profile_picture
        FROM patients p
        JOIN users u ON p.user_id = u.id
        WHERE p.id = $1
        """,
        str(patient_id)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Patient not found")
    return dict(row)


@router.post("/patients", response_model=PatientOut)
async def create_patient(payload: PatientCreate):
    """Create a new patient record"""
    row = await db.fetchrow(
        """
        INSERT INTO patients
        (user_id, date_of_birth, phone, mci_stage, diagnosis_date, assigned_doctor_id, notes)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *
        """,
        str(payload.user_id),
        payload.date_of_birth,
        payload.phone,
        payload.mci_stage,
        payload.diagnosis_date,
        str(payload.assigned_doctor_id) if payload.assigned_doctor_id else None,
        payload.notes
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create patient")
    return dict(row)


@router.put("/patients/{patient_id}/stage")
async def update_mci_stage(
    patient_id: UUID,
    mci_stage: str = Query(..., description="New MCI stage"),
    doctor_id: str = Query(..., description="Doctor making the update")
):
    """Update patient's MCI stage"""
    result = await db.execute(
        """
        UPDATE patients
        SET mci_stage = $1, diagnosis_date = NOW()
        WHERE id = $2
        """,
        mci_stage,
        str(patient_id)
    )
    if result.endswith("0"):
        raise HTTPException(status_code=404, detail="Patient not found")

    # Log the update in audit_logs
    await db.execute(
        """
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details)
        VALUES ($1, $2, $3, $4, $5)
        """,
        doctor_id,
        "update_mci_stage",
        "patient",
        str(patient_id),
        {"mci_stage": mci_stage}
    )

    return {"status": "ok", "mci_stage": mci_stage}


@router.get("/patients/{patient_id}/recordings", response_model=List[RecordingOut])
async def get_recordings(patient_id: UUID):
    """Get all voice recordings for a patient"""
    rows = await db.fetch(
        """
        SELECT * FROM recordings
        WHERE patient_id = $1
        ORDER BY recorded_at DESC
        LIMIT 100
        """,
        str(patient_id)
    )
    return [dict(r) for r in rows]


@router.get("/patients/{patient_id}/assessments", response_model=List[VoiceAssessmentOut])
async def get_voice_assessments(patient_id: UUID):
    """Get all voice assessments for a patient"""
    rows = await db.fetch(
        """
        SELECT va.*
        FROM voice_assessments va
        JOIN recordings r ON va.recording_id = r.id
        WHERE r.patient_id = $1
        ORDER BY va.assessed_at DESC
        LIMIT 100
        """,
        str(patient_id)
    )
    return [dict(r) for r in rows]


@router.get("/patients/{patient_id}/mri", response_model=List[MRIAssessmentOut])
async def get_mri_results(patient_id: UUID):
    """Get all MRI assessments for a patient"""
    rows = await db.fetch(
        """
        SELECT * FROM mri_assessments
        WHERE patient_id = $1
        ORDER BY scan_date DESC
        LIMIT 50
        """,
        str(patient_id)
    )
    return [dict(r) for r in rows]


@router.get("/patients/{patient_id}/progress")
async def get_progress(patient_id: UUID):
    """Get patient progress over time (voice scores, MRI results)"""
    # Voice assessment scores over time
    voice_scores = await db.fetch(
        """
        SELECT va.assessed_at, va.cognitive_score, va.flag
        FROM voice_assessments va
        JOIN recordings r ON va.recording_id = r.id
        WHERE r.patient_id = $1
        ORDER BY va.assessed_at ASC
        """,
        str(patient_id)
    )

    # MRI classifications over time
    mri_results = await db.fetch(
        """
        SELECT scan_date, classification, confidence
        FROM mri_assessments
        WHERE patient_id = $1
        ORDER BY scan_date ASC
        """,
        str(patient_id)
    )

    return {
        "voice_scores": [dict(r) for r in voice_scores],
        "mri_results": [dict(r) for r in mri_results]
    }


@router.post("/diagnoses", response_model=DiagnosisOut)
async def create_diagnosis(payload: DiagnosisCreate):
    """Create a new diagnosis for a patient"""
    row = await db.fetchrow(
        """
        INSERT INTO diagnoses
        (patient_id, doctor_id, mci_stage, confidence, based_on_mri, based_on_voice, notes, follow_up_date)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING *
        """,
        str(payload.patient_id),
        str(payload.doctor_id),
        payload.mci_stage,
        payload.confidence,
        str(payload.based_on_mri) if payload.based_on_mri else None,
        str(payload.based_on_voice) if payload.based_on_voice else None,
        payload.notes,
        payload.follow_up_date
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create diagnosis")

    # Update patient's mci_stage
    await db.execute(
        "UPDATE patients SET mci_stage = $1, diagnosis_date = NOW() WHERE id = $2",
        payload.mci_stage,
        str(payload.patient_id)
    )

    # TODO: Send notification to patient and family

    return dict(row)


@router.get("/patients/{patient_id}/diagnoses", response_model=List[DiagnosisOut])
async def get_diagnoses(patient_id: UUID):
    """Get diagnosis history for a patient"""
    rows = await db.fetch(
        """
        SELECT * FROM diagnoses
        WHERE patient_id = $1
        ORDER BY diagnosis_date DESC
        """,
        str(patient_id)
    )
    return [dict(r) for r in rows]


@router.put("/diagnoses/{diagnosis_id}", response_model=DiagnosisOut)
async def update_diagnosis(diagnosis_id: UUID, payload: DiagnosisUpdate):
    """Update an existing diagnosis"""
    # Build update query dynamically based on provided fields
    updates = []
    values = []
    param_count = 1

    if payload.mci_stage is not None:
        updates.append(f"mci_stage = ${param_count}")
        values.append(payload.mci_stage)
        param_count += 1

    if payload.confidence is not None:
        updates.append(f"confidence = ${param_count}")
        values.append(payload.confidence)
        param_count += 1

    if payload.notes is not None:
        updates.append(f"notes = ${param_count}")
        values.append(payload.notes)
        param_count += 1

    if payload.follow_up_date is not None:
        updates.append(f"follow_up_date = ${param_count}")
        values.append(payload.follow_up_date)
        param_count += 1

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    values.append(str(diagnosis_id))
    query = f"UPDATE diagnoses SET {', '.join(updates)} WHERE id = ${param_count} RETURNING *"

    row = await db.fetchrow(query, *values)
    if not row:
        raise HTTPException(status_code=404, detail="Diagnosis not found")

    return dict(row)


@router.get("/alerts")
async def list_alerts(doctor_id: str = Query(...)):
    """List all flagged assessments (warning/critical) for this doctor's patients"""
    rows = await db.fetch(
        """
        SELECT va.*, r.patient_id, r.audio_path, u.name as patient_name
        FROM voice_assessments va
        JOIN recordings r ON va.recording_id = r.id
        JOIN patients p ON r.patient_id = p.id
        JOIN users u ON p.user_id = u.id
        WHERE p.assigned_doctor_id = $1
          AND va.flag IN ('warning', 'critical')
        ORDER BY va.assessed_at DESC
        LIMIT 100
        """,
        doctor_id
    )
    return [dict(r) for r in rows]


@router.put("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: UUID, doctor_id: str = Query(...)):
    """Mark an alert as reviewed (implemented as adding a note in audit log)"""
    # Check if alert exists
    assessment = await db.fetchrow(
        "SELECT * FROM voice_assessments WHERE id = $1",
        str(alert_id)
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Log the resolution
    await db.execute(
        """
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details)
        VALUES ($1, $2, $3, $4, $5)
        """,
        doctor_id,
        "resolve_alert",
        "voice_assessment",
        str(alert_id),
        {"flag": assessment["flag"], "reviewed": True}
    )

    return {"status": "ok", "message": "Alert marked as reviewed"}


@router.get("/patients/{patient_id}/family", response_model=List[FamilyMemberOut])
async def list_family(patient_id: UUID):
    """List family members for a patient"""
    rows = await db.fetch(
        """
        SELECT fm.*, u.name, u.email
        FROM family_members fm
        JOIN users u ON fm.user_id = u.id
        WHERE fm.patient_id = $1
        ORDER BY fm.created_at DESC
        """,
        str(patient_id)
    )
    return [dict(r) for r in rows]


@router.post("/patients/{patient_id}/family", response_model=FamilyMemberOut)
async def approve_family(patient_id: UUID, payload: FamilyMemberCreate, doctor_id: str = Query(...)):
    """Approve family member access to patient data"""
    row = await db.fetchrow(
        """
        INSERT INTO family_members
        (user_id, patient_id, relationship, can_view_recordings, can_view_transcripts, can_view_scores, approved_by, approved_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
        RETURNING *
        """,
        str(payload.user_id),
        str(patient_id),
        payload.relationship,
        payload.can_view_recordings,
        payload.can_view_transcripts,
        payload.can_view_scores,
        doctor_id
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to approve family member")

    # TODO: Send notification to family member

    return dict(row)


@router.delete("/patients/{patient_id}/family/{family_id}")
async def remove_family(patient_id: UUID, family_id: UUID, doctor_id: str = Query(...)):
    """Remove family member access"""
    result = await db.execute(
        """
        DELETE FROM family_members
        WHERE id = $1 AND patient_id = $2
        """,
        str(family_id),
        str(patient_id)
    )
    if result.endswith("0"):
        raise HTTPException(status_code=404, detail="Family member not found")

    # Log the removal
    await db.execute(
        """
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id)
        VALUES ($1, $2, $3, $4)
        """,
        doctor_id,
        "remove_family_access",
        "family_member",
        str(family_id)
    )

    return {"status": "ok", "message": "Family access removed"}
