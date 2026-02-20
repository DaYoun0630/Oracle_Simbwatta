#!/usr/bin/env python3
"""
Import ADNI baseline cohort CSV into the platform schema.

Targets:
- users
- patients
- visits
- clinical_tests
- neuropsych_tests
- biomarkers
- mri_assessments (image_id linkage + predicted stage compatibility)
- data_ingest_runs (ingestion audit)
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
    # Requested project convention:
    # subtype 1 -> sMCI, subtype 2 -> pMCI
    # doctor can always override later via diagnosis flow.
    m = (mci_subtype or "").strip()
    if m == "1":
        return "sMCI"
    if m == "2":
        return "pMCI"
    return "unknown"


def to_mri_classification(stage: str) -> Optional[str]:
    mapping = {
        "CN": "CN",
        "sMCI": "EMCI",
        "pMCI": "LMCI",
        "AD": "AD",
    }
    return mapping.get(stage)


def discover_csv(explicit_path: Optional[str]) -> str:
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
    sid = (subject_id or "").strip()
    identifier = sid if sid else f"RID{rid}" if rid is not None else str(uuid.uuid4())[:8]
    email = f"{identifier.lower()}@adni.local"
    name = f"ADNI {identifier}"
    user_id = str(uuid.uuid4())

    cur.execute(
        """
        INSERT INTO users (id, email, name, role, created_at, updated_at)
        VALUES (%s, %s, %s, 'patient', NOW(), NOW())
        ON CONFLICT (email) DO UPDATE
          SET name = EXCLUDED.name,
              role = 'patient',
              updated_at = NOW()
        RETURNING id
        """,
        (user_id, email, name),
    )
    return str(cur.fetchone()[0])


def find_patient(cur, subject_id: Optional[str], rid: Optional[int]) -> Optional[str]:
    sid = (subject_id or "").strip()
    if sid:
        cur.execute("SELECT id FROM patients WHERE subject_id = %s LIMIT 1", (sid,))
        row = cur.fetchone()
        if row:
            return str(row[0])

    if rid is not None:
        cur.execute("SELECT id FROM patients WHERE rid = %s LIMIT 1", (rid,))
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
    hospital: Optional[str],
) -> Tuple[str, bool]:
    patient_id = find_patient(cur, subject_id, rid)
    stage = normalize_stage(row.get("mci_subtype"))

    payload = {
        "rid": rid,
        "subject_id": (subject_id or "").strip() or None,
        "gender": parse_int(row.get("gender")),
        "ptdobyy": parse_date(row.get("ptdobyy")),
        "apoe4": parse_int(row.get("apoe4")),
        "enrollment_date": exam_date,
        "hospital": hospital,
        "mci_stage": stage,
    }

    if patient_id:
        cur.execute(
            """
            UPDATE patients
            SET user_id = %s,
                rid = %s,
                subject_id = %s,
                gender = %s,
                ptdobyy = %s,
                apoe4 = %s,
                enrollment_date = COALESCE(enrollment_date, %s),
                hospital = COALESCE(%s, hospital),
                mci_stage = CASE WHEN mci_stage IS NULL OR mci_stage = 'unknown' THEN %s ELSE mci_stage END,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                user_id,
                payload["rid"],
                payload["subject_id"],
                payload["gender"],
                payload["ptdobyy"],
                payload["apoe4"],
                payload["enrollment_date"],
                payload["hospital"],
                payload["mci_stage"],
                patient_id,
            ),
        )
        return patient_id, False

    new_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO patients (
            id, user_id, rid, subject_id, gender, ptdobyy, apoe4,
            enrollment_date, hospital, mci_stage, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, NOW(), NOW()
        )
        """,
        (
            new_id,
            user_id,
            payload["rid"],
            payload["subject_id"],
            payload["gender"],
            payload["ptdobyy"],
            payload["apoe4"],
            payload["enrollment_date"],
            payload["hospital"],
            payload["mci_stage"],
        ),
    )
    return new_id, True


def main() -> int:
    parser = argparse.ArgumentParser(description="Import ADNI baseline cohort CSV into PostgreSQL.")
    parser.add_argument("--csv", help="Path to ADNI CSV (auto-detected if omitted).")
    parser.add_argument(
        "--db-url",
        default=os.getenv("DATABASE_URL", "postgresql://mci_user:change_me1@localhost:5432/cognitive"),
        help="PostgreSQL connection string.",
    )
    parser.add_argument("--hospital", default="ADNI", help="Default hospital label for imported patients.")
    parser.add_argument("--dry-run", action="store_true", help="Load and validate rows, then rollback.")
    args = parser.parse_args()

    csv_path = discover_csv(args.csv)
    counters = Counters()
    errors = []

    conn = psycopg2.connect(args.db_url, options="-c timezone=Asia/Seoul")
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO data_ingest_runs (source_name, source_file, status, started_at)
                VALUES (%s, %s, 'running', NOW())
                RETURNING id
                """,
                ("adni_baseline_csv", os.path.abspath(csv_path)),
            )
            run_id = str(cur.fetchone()[0])

            with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader, start=1):
                    counters.rows_total += 1
                    cur.execute("SAVEPOINT adni_row_sp")
                    try:
                        rid = parse_int(row.get("rid"))
                        subject_id = row.get("subject_id")
                        exam_date = parse_date(row.get("examdate"))

                        user_id = upsert_user(cur, subject_id, rid)
                        counters.users_upserted += 1

                        patient_id, inserted = upsert_patient(
                            cur,
                            user_id=user_id,
                            subject_id=subject_id,
                            rid=rid,
                            exam_date=exam_date,
                            row=row,
                            hospital=args.hospital,
                        )
                        if inserted:
                            counters.patients_inserted += 1
                        else:
                            counters.patients_updated += 1

                        viscode2 = (row.get("viscode2") or "").strip() or "sc"
                        origprot = (row.get("origprot") or "").strip() or None
                        colprot = (row.get("colprot") or "").strip() or None
                        image_id = parse_int(row.get("image_id"))

                        cur.execute(
                            """
                            INSERT INTO visits (
                                id, patient_id, exam_date, viscode2, origprot, colprot, image_id, notes, created_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                            )
                            ON CONFLICT (patient_id, exam_date, viscode2) DO UPDATE
                              SET origprot = EXCLUDED.origprot,
                                  colprot = EXCLUDED.colprot,
                                  image_id = EXCLUDED.image_id
                            RETURNING id
                            """,
                            (
                                str(uuid.uuid4()),
                                patient_id,
                                exam_date,
                                viscode2,
                                origprot,
                                colprot,
                                image_id,
                                "Imported from ADNI baseline CSV",
                            ),
                        )
                        visit_id = str(cur.fetchone()[0])
                        counters.visits_upserted += 1

                        cur.execute(
                            """
                            INSERT INTO clinical_tests (
                                id, patient_id, visit_id, exam_date, viscode2,
                                mmse, moca, adas_cog13, cdr_global, cdr_memory, cdr_sb,
                                faq, gds, cci, nxaudito, notes, created_at
                            ) VALUES (
                                %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, NOW()
                            )
                            ON CONFLICT (patient_id, exam_date, viscode2) DO UPDATE
                              SET visit_id = EXCLUDED.visit_id,
                                  mmse = EXCLUDED.mmse,
                                  moca = EXCLUDED.moca,
                                  adas_cog13 = EXCLUDED.adas_cog13,
                                  cdr_global = EXCLUDED.cdr_global,
                                  cdr_memory = EXCLUDED.cdr_memory,
                                  cdr_sb = EXCLUDED.cdr_sb,
                                  faq = EXCLUDED.faq,
                                  gds = EXCLUDED.gds,
                                  cci = EXCLUDED.cci,
                                  nxaudito = EXCLUDED.nxaudito
                            """,
                            (
                                str(uuid.uuid4()),
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

                        cur.execute(
                            """
                            INSERT INTO neuropsych_tests (
                                id, patient_id, visit_id, exam_date, viscode2,
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
                            ON CONFLICT (patient_id, exam_date, viscode2) DO UPDATE
                              SET visit_id = EXCLUDED.visit_id,
                                  avtot1 = EXCLUDED.avtot1,
                                  avtot2 = EXCLUDED.avtot2,
                                  avtot3 = EXCLUDED.avtot3,
                                  avtot4 = EXCLUDED.avtot4,
                                  avtot5 = EXCLUDED.avtot5,
                                  avtot6 = EXCLUDED.avtot6,
                                  avtotb = EXCLUDED.avtotb,
                                  avdel30min = EXCLUDED.avdel30min,
                                  avdeltot = EXCLUDED.avdeltot,
                                  averr1 = EXCLUDED.averr1,
                                  averr2 = EXCLUDED.averr2,
                                  ravlt_immediate = EXCLUDED.ravlt_immediate,
                                  ravlt_learning = EXCLUDED.ravlt_learning,
                                  ravlt_forgetting = EXCLUDED.ravlt_forgetting,
                                  ravlt_pct_forgetting = EXCLUDED.ravlt_pct_forgetting,
                                  traascor = EXCLUDED.traascor,
                                  trabscor = EXCLUDED.trabscor
                            """,
                            (
                                str(uuid.uuid4()),
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

                        biomarker_fields = [
                            row.get("ABETA40"),
                            row.get("ABETA42"),
                            row.get("PTAU"),
                            row.get("TAU"),
                            row.get("AB42/AB40"),
                            row.get("ptau/AB42"),
                            row.get("ttau/AB42"),
                        ]
                        if any((v or "").strip() for v in biomarker_fields):
                            cur.execute(
                                """
                                INSERT INTO biomarkers (
                                    id, patient_id, visit_id, collected_date, sample_type,
                                    abeta42, abeta40, ptau, tau, ab42_ab40, ptau_ab42, ttau_ab42,
                                    notes, created_at
                                ) VALUES (
                                    %s, %s, %s, %s, 'csf',
                                    %s, %s, %s, %s, %s, %s, %s,
                                    %s, NOW()
                                )
                                ON CONFLICT (patient_id, collected_date, sample_type) DO UPDATE
                                  SET visit_id = EXCLUDED.visit_id,
                                      abeta42 = EXCLUDED.abeta42,
                                      abeta40 = EXCLUDED.abeta40,
                                      ptau = EXCLUDED.ptau,
                                      tau = EXCLUDED.tau,
                                      ab42_ab40 = EXCLUDED.ab42_ab40,
                                      ptau_ab42 = EXCLUDED.ptau_ab42,
                                      ttau_ab42 = EXCLUDED.ttau_ab42
                                """,
                                (
                                    str(uuid.uuid4()),
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

                        if image_id is not None:
                            stage = normalize_stage(row.get("mci_subtype"))
                            classification = to_mri_classification(stage)
                            cur.execute(
                                """
                                SELECT id FROM mri_assessments
                                WHERE patient_id = %s AND image_id = %s
                                ORDER BY created_at DESC NULLS LAST, processed_at DESC NULLS LAST
                                LIMIT 1
                                """,
                                (patient_id, image_id),
                            )
                            found = cur.fetchone()

                            if found:
                                mri_id = str(found[0])
                                cur.execute(
                                    """
                                    UPDATE mri_assessments
                                    SET scan_date = COALESCE(scan_date, %s),
                                        classification = COALESCE(classification, %s),
                                        predicted_stage = COALESCE(predicted_stage, %s),
                                        preprocessing_status = COALESCE(preprocessing_status, 'pending'),
                                        created_at = COALESCE(created_at, NOW())
                                    WHERE id = %s
                                    """,
                                    (exam_date, classification, stage, mri_id),
                                )
                            else:
                                mri_id = str(uuid.uuid4())
                                cur.execute(
                                    """
                                    INSERT INTO mri_assessments (
                                        id, patient_id, scan_date, file_path, classification,
                                        model_version, processed_at, image_id, preprocessing_status,
                                        predicted_stage, created_at
                                    ) VALUES (
                                        %s, %s, %s, %s, %s,
                                        %s, NULL, %s, 'pending',
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

                            cur.execute(
                                "UPDATE visits SET mri_assessment_id = %s WHERE id = %s",
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
                WHERE id = %s
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
            conn.rollback()
        else:
            conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print("ADNI import summary")
    print(f"  csv: {csv_path}")
    print(f"  rows_total: {counters.rows_total}")
    print(f"  rows_ok: {counters.rows_ok}")
    print(f"  rows_failed: {counters.rows_failed}")
    print(f"  patients_inserted: {counters.patients_inserted}")
    print(f"  patients_updated: {counters.patients_updated}")
    print(f"  visits_upserted: {counters.visits_upserted}")
    print(f"  clinical_upserted: {counters.clinical_upserted}")
    print(f"  neuropsych_upserted: {counters.neuropsych_upserted}")
    print(f"  biomarkers_upserted: {counters.biomarkers_upserted}")
    print(f"  mri_upserted: {counters.mri_upserted}")
    if errors:
        print("  first_errors:")
        for line in errors[:5]:
            print(f"    - {line}")

    return 0 if counters.rows_failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
