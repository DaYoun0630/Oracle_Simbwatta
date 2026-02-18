#!/usr/bin/env python3
"""
Import ADNI baseline cohort CSV into the 004 schema (English table names).

Updated for 004_mci_full_schema.sql:
- users (user_id PK, no role column)
- patients (user_id PK, date_of_birth, no mci_stage/hospital)
- clinical_assessments (renamed from clinical_tests)
- visits, neuropsych_tests, biomarkers, mri_assessments
- data_ingest_runs
"""

from __future__ import annotations

import argparse
import csv
import glob
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, Optional, Tuple

import psycopg2


def parse_int(value: str) -> Optional[int]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def parse_float(value: str) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def first_non_none(*values):
    for value in values:
        if value is not None:
            return value
    return None


def parse_date(value: str) -> Optional[date]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def normalize_stage(mci_subtype: Optional[str]) -> str:
    """Convert mci_subtype to stage classification."""
    m = (mci_subtype or "").strip()
    if m == "1":
        return "sMCI"
    if m == "2":
        return "pMCI"
    return "unknown"


def to_mri_classification(stage: str) -> Optional[str]:
    """Map stage to MRI classification."""
    mapping = {
        "CN": "CN",
        "sMCI": "EMCI",
        "pMCI": "LMCI",
        "AD": "AD",
    }
    return mapping.get(stage)


def discover_csv(explicit_path: Optional[str]) -> str:
    """Find ADNI CSV file."""
    if explicit_path:
        if not os.path.exists(explicit_path):
            raise FileNotFoundError(f"CSV not found: {explicit_path}")
        return explicit_path

    candidates = sorted(glob.glob("adni3_baseline_cohort_mci*.csv"))
    if not candidates:
        raise FileNotFoundError("No ADNI CSV found. Expected pattern: adni3_baseline_cohort_mci*.csv")
    return candidates[0]


@dataclass
class Counters:
    rows_total: int = 0
    rows_ok: int = 0
    rows_failed: int = 0
    users_upserted: int = 0
    patients_inserted: int = 0
    patients_updated: int = 0
    visits_upserted: int = 0
    clinical_upserted: int = 0
    neuropsych_upserted: int = 0
    biomarkers_upserted: int = 0
    mri_upserted: int = 0


def upsert_user(cur, subject_id: Optional[str], rid: Optional[int]) -> str:
    """Upsert user, return user_id."""
    sid = (subject_id or "").strip()
    identifier = sid if sid else f"RID{rid}" if rid is not None else str(uuid.uuid4())[:8]
    email = f"{identifier.lower()}@adni.local"
    name = f"ADNI {identifier}"

    # Check if user exists by email
    cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
    existing = cur.fetchone()

    if existing:
        user_id = str(existing[0])
        cur.execute(
            """
            UPDATE users
            SET name = %s, updated_at = NOW()
            WHERE user_id = %s
            """,
            (name, user_id),
        )
    else:
        user_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO users (user_id, email, name, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            """,
            (user_id, email, name),
        )

    return user_id


def find_patient(cur, subject_id: Optional[str], rid: Optional[int]) -> Optional[str]:
    """Find patient by subject_id or rid."""
    sid = (subject_id or "").strip()
    if sid:
        cur.execute("SELECT user_id FROM patients WHERE subject_id = %s LIMIT 1", (sid,))
        row = cur.fetchone()
        if row:
            return str(row[0])

    if rid is not None:
        cur.execute("SELECT user_id FROM patients WHERE rid = %s LIMIT 1", (rid,))
        row = cur.fetchone()
        if row:
            return str(row[0])

    return None


def upsert_patient(
    cur,
    user_id: str,
    subject_id: Optional[str],
    rid: Optional[int],
    exam_date: Optional[date],
    row: Dict[str, str],
) -> Tuple[str, bool]:
    """Upsert patient, return (patient_id, is_new)."""
    patient_id = find_patient(cur, subject_id, rid)

    payload = {
        "rid": rid,
        "subject_id": (subject_id or "").strip() or None,
        "gender": parse_int(row.get("gender")),
        "date_of_birth": parse_date(row.get("ptdobyy")),
        "pteducat": parse_int(row.get("pteducat")),
        "apoe4": parse_int(row.get("apoe4")),
        "enrollment_date": exam_date or date.today(),
    }

    if patient_id:
        # Update existing patient
        cur.execute(
            """
            UPDATE patients
            SET user_id = %s,
                rid = %s,
                subject_id = %s,
                gender = %s,
                date_of_birth = %s,
                pteducat = COALESCE(%s, pteducat),
                apoe4 = %s,
                enrollment_date = COALESCE(enrollment_date, %s),
                updated_at = NOW()
            WHERE user_id = %s
            """,
            (
                user_id,
                payload["rid"],
                payload["subject_id"],
                payload["gender"],
                payload["date_of_birth"],
                payload["pteducat"],
                payload["apoe4"],
                payload["enrollment_date"],
                patient_id,
            ),
        )
        return patient_id, False

    # Insert new patient
    cur.execute(
        """
        INSERT INTO patients (
            user_id, rid, subject_id, gender, date_of_birth, pteducat, apoe4,
            enrollment_date, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, NOW(), NOW()
        )
        """,
        (
            user_id,
            payload["rid"],
            payload["subject_id"],
            payload["gender"],
            payload["date_of_birth"],
            payload["pteducat"],
            payload["apoe4"],
            payload["enrollment_date"],
        ),
    )
    return user_id, True


def upsert_visit(cur, patient_id: str, exam_date: Optional[date], viscode2: str, row: Dict) -> str:
    """Upsert visit, return visit_id."""
    origprot = (row.get("origprot") or "").strip() or None
    colprot = (row.get("colprot") or "").strip() or None
    image_id = parse_int(row.get("image_id"))

    # Check if visit exists
    cur.execute(
        """
        SELECT visit_id FROM visits
        WHERE patient_id = %s AND exam_date = %s AND viscode2 = %s
        LIMIT 1
        """,
        (patient_id, exam_date, viscode2),
    )
    existing = cur.fetchone()

    if existing:
        visit_id = str(existing[0])
        cur.execute(
            """
            UPDATE visits
            SET origprot = %s, colprot = %s, image_id = %s
            WHERE visit_id = %s
            """,
            (origprot, colprot, image_id, visit_id),
        )
    else:
        visit_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO visits (
                visit_id, patient_id, exam_date, viscode2, origprot, colprot, image_id,
                notes, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                'Imported from ADNI baseline CSV', NOW()
            )
            """,
            (visit_id, patient_id, exam_date, viscode2, origprot, colprot, image_id),
        )

    return visit_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Import ADNI baseline cohort CSV into PostgreSQL (004 schema).")
    parser.add_argument("--csv", help="Path to ADNI CSV (auto-detected if omitted).")
    parser.add_argument(
        "--db-url",
        default=os.getenv("DATABASE_URL", "postgresql://mci_user:change_me1@localhost:5432/cognitive"),
        help="PostgreSQL connection string.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Load and validate rows, then rollback.")
    args = parser.parse_args()

    csv_path = discover_csv(args.csv)
    counters = Counters()
    errors = []

    conn = psycopg2.connect(args.db_url, options="-c timezone=Asia/Seoul")
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            # Start ingestion run
            run_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO data_ingest_runs (run_id, source_name, source_file, status, started_at, created_at)
                VALUES (%s, %s, %s, 'running', NOW(), NOW())
                """,
                (run_id, "adni_baseline_csv", os.path.abspath(csv_path)),
            )

            with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader, start=1):
                    counters.rows_total += 1
                    cur.execute("SAVEPOINT adni_row_sp")

                    try:
                        rid = parse_int(row.get("rid"))
                        subject_id = row.get("subject_id")
                        exam_date = parse_date(row.get("examdate"))

                        # 1. Upsert user
                        user_id = upsert_user(cur, subject_id, rid)
                        counters.users_upserted += 1

                        # 2. Upsert patient
                        patient_id, inserted = upsert_patient(
                            cur,
                            user_id=user_id,
                            subject_id=subject_id,
                            rid=rid,
                            exam_date=exam_date,
                            row=row,
                        )
                        if inserted:
                            counters.patients_inserted += 1
                        else:
                            counters.patients_updated += 1

                        # 3. Upsert visit
                        viscode2 = (row.get("viscode2") or "").strip() or "sc"
                        visit_id = upsert_visit(cur, patient_id, exam_date, viscode2, row)
                        counters.visits_upserted += 1

                        # 4. Upsert clinical_assessments
                        assessment_id = str(uuid.uuid4())
                        cur.execute(
                            """
                            INSERT INTO clinical_assessments (
                                assessment_id, patient_id, visit_id, exam_date, viscode2,
                                mmse, moca, adas_cog13, cdr_global, cdr_memory, cdr_sb,
                                faq, gds, cci, nxaudito, notes, created_at
                            ) VALUES (
                                %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, NOW()
                            )
                            ON CONFLICT DO NOTHING
                            """,
                            (
                                assessment_id,
                                patient_id,
                                visit_id,
                                exam_date,
                                viscode2,
                                parse_int(row.get("mmse")),
                                parse_float(row.get("moca")),
                                parse_float(row.get("adas_cog13")),
                                parse_float(row.get("cdr_global")),
                                parse_float(row.get("cdr_memory")),
                                parse_float(row.get("cdr_sb")),
                                parse_float(row.get("faq")),
                                parse_float(row.get("gds")),
                                parse_float(row.get("cci")),
                                parse_int(row.get("nxaudito")),
                                "Imported from ADNI baseline CSV",
                            ),
                        )
                        counters.clinical_upserted += 1

                        # 5. Upsert neuropsych_tests
                        test_id = str(uuid.uuid4())
                        cur.execute(
                            """
                            INSERT INTO neuropsych_tests (
                                test_id, patient_id, visit_id, exam_date, viscode2,
                                avtot1, avtot2, avtot3, avtot4, avtot5, avtot6, avtotb,
                                avdel30min, avdeltot, averr1, averr2,
                                ravlt_immediate, ravlt_learning, ravlt_forgetting, ravlt_pct_forgetting,
                                traascor, trabscor, notes, created_at
                            ) VALUES (
                                %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s,
                                %s, %s, %s, %s,
                                %s, %s, %s, NOW()
                            )
                            ON CONFLICT DO NOTHING
                            """,
                            (
                                test_id,
                                patient_id,
                                visit_id,
                                exam_date,
                                viscode2,
                                parse_float(row.get("AVTOT1")),
                                parse_float(row.get("AVTOT2")),
                                parse_float(row.get("AVTOT3")),
                                parse_float(row.get("AVTOT4")),
                                parse_float(row.get("AVTOT5")),
                                parse_float(row.get("AVTOT6")),
                                parse_float(row.get("AVTOTB")),
                                parse_float(row.get("AVDEL30MIN")),
                                first_non_none(
                                    parse_float(row.get("ldeltotal")),
                                    parse_float(row.get("LDELTOTAL")),
                                    parse_float(row.get("AVDELTOT")),
                                    parse_float(row.get("avdeltot")),
                                ),
                                parse_float(row.get("AVERR1")),
                                parse_float(row.get("AVERR2")),
                                parse_float(row.get("RAVLT_immediate")),
                                parse_float(row.get("RAVLT_learning")),
                                parse_float(row.get("RAVLT_forgetting")),
                                parse_float(row.get("RAVLT_pct_forgetting")),
                                parse_float(row.get("TRAASCOR")),
                                parse_float(row.get("TRABSCOR")),
                                "Imported from ADNI baseline CSV",
                            ),
                        )
                        counters.neuropsych_upserted += 1

                        # 6. Upsert biomarkers (if data exists)
                        biomarker_fields = [
                            row.get("ABETA40"),
                            row.get("ABETA42"),
                            row.get("PTAU"),
                            row.get("TAU"),
                        ]
                        if any((v or "").strip() for v in biomarker_fields):
                            biomarker_id = str(uuid.uuid4())
                            cur.execute(
                                """
                                INSERT INTO biomarkers (
                                    biomarker_id, patient_id, visit_id, collected_date, sample_type,
                                    abeta42, abeta40, ptau, tau, ab42_ab40, ptau_ab42, ttau_ab42,
                                    notes, created_at
                                ) VALUES (
                                    %s, %s, %s, %s, 'csf',
                                    %s, %s, %s, %s, %s, %s, %s,
                                    %s, NOW()
                                )
                                ON CONFLICT DO NOTHING
                                """,
                                (
                                    biomarker_id,
                                    patient_id,
                                    visit_id,
                                    exam_date,
                                    parse_float(row.get("ABETA42")),
                                    parse_float(row.get("ABETA40")),
                                    parse_float(row.get("PTAU")),
                                    parse_float(row.get("TAU")),
                                    parse_float(row.get("AB42/AB40")),
                                    parse_float(row.get("ptau/AB42")),
                                    parse_float(row.get("ttau/AB42")),
                                    "Imported from ADNI baseline CSV",
                                ),
                            )
                            counters.biomarkers_upserted += 1

                        # 7. Upsert MRI assessments (if image_id exists)
                        image_id = parse_int(row.get("image_id"))
                        if image_id is not None:
                            stage = normalize_stage(row.get("mci_subtype"))
                            classification = to_mri_classification(stage)

                            # Check if MRI exists
                            cur.execute(
                                """
                                SELECT assessment_id FROM mri_assessments
                                WHERE patient_id = %s AND image_id = %s
                                LIMIT 1
                                """,
                                (patient_id, image_id),
                            )
                            existing_mri = cur.fetchone()

                            if existing_mri:
                                mri_id = str(existing_mri[0])
                                cur.execute(
                                    """
                                    UPDATE mri_assessments
                                    SET scan_date = COALESCE(scan_date, %s),
                                        classification = COALESCE(classification, %s),
                                        predicted_stage = COALESCE(predicted_stage, %s),
                                        preprocessing_status = COALESCE(preprocessing_status, 'pending')
                                    WHERE assessment_id = %s
                                    """,
                                    (exam_date, classification, stage, mri_id),
                                )
                            else:
                                mri_id = str(uuid.uuid4())
                                cur.execute(
                                    """
                                    INSERT INTO mri_assessments (
                                        assessment_id, patient_id, scan_date, file_path, classification,
                                        model_version, image_id, preprocessing_status,
                                        predicted_stage, created_at
                                    ) VALUES (
                                        %s, %s, %s, %s, %s,
                                        %s, %s, 'pending',
                                        %s, NOW()
                                    )
                                    """,
                                    (
                                        mri_id,
                                        patient_id,
                                        exam_date,
                                        f"mri-scans/{subject_id or rid}/{image_id}",
                                        classification,
                                        "adni_baseline_import",
                                        image_id,
                                        stage,
                                    ),
                                )

                            # Link MRI to visit
                            cur.execute(
                                "UPDATE visits SET mri_assessment_id = %s WHERE visit_id = %s",
                                (mri_id, visit_id),
                            )
                            counters.mri_upserted += 1

                        counters.rows_ok += 1
                        cur.execute("RELEASE SAVEPOINT adni_row_sp")

                    except Exception as exc:
                        counters.rows_failed += 1
                        errors.append(f"row {idx}: {exc}")
                        cur.execute("ROLLBACK TO SAVEPOINT adni_row_sp")
                        cur.execute("RELEASE SAVEPOINT adni_row_sp")

            # Update ingestion run
            status = "failed" if counters.rows_failed > 0 else "completed"
            cur.execute(
                """
                UPDATE data_ingest_runs
                SET status = %s,
                    rows_total = %s,
                    rows_inserted = %s,
                    rows_updated = %s,
                    rows_failed = %s,
                    error_log = %s,
                    finished_at = NOW()
                WHERE run_id = %s
                """,
                (
                    status,
                    counters.rows_total,
                    counters.patients_inserted,
                    counters.patients_updated,
                    counters.rows_failed,
                    "\n".join(errors[:200]) if errors else None,
                    run_id,
                ),
            )

        if args.dry_run:
            print("DRY RUN: Rolling back...")
            conn.rollback()
        else:
            conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print("\n" + "="*60)
    print("ADNI Import Summary (004 Schema)")
    print("="*60)
    print(f"CSV File:              {csv_path}")
    print(f"Total Rows:            {counters.rows_total}")
    print(f"Successful:            {counters.rows_ok}")
    print(f"Failed:                {counters.rows_failed}")
    print(f"Users Upserted:        {counters.users_upserted}")
    print(f"Patients Inserted:     {counters.patients_inserted}")
    print(f"Patients Updated:      {counters.patients_updated}")
    print(f"Visits:                {counters.visits_upserted}")
    print(f"Clinical Assessments:  {counters.clinical_upserted}")
    print(f"Neuropsych Tests:      {counters.neuropsych_upserted}")
    print(f"Biomarkers:            {counters.biomarkers_upserted}")
    print(f"MRI Assessments:       {counters.mri_upserted}")

    if errors:
        print("\nFirst 5 Errors:")
        for line in errors[:5]:
            print(f"  - {line}")

    print("="*60 + "\n")

    return 0 if counters.rows_failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
