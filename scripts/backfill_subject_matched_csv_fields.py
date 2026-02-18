#!/usr/bin/env python3
"""
Backfill key clinical fields from ADNI CSV into existing DB rows by subject_id match.

Targets:
- patients.apoe4, patients.pteducat
- latest clinical_assessments: cdr_sb, nxaudito
- latest neuropsych_tests: avdeltot (uses CSV ldeltotal first, then avdeltot)

This script uses `docker exec mci-postgres psql` so it does not require psycopg2.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from typing import Dict, Optional, Tuple


def parse_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def parse_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def sql_num(value: Optional[float]) -> str:
    return "NULL" if value is None else str(value)


def run_psql_query(container: str, user: str, db: str, sql: str) -> str:
    cmd = [
        "docker",
        "exec",
        "-i",
        container,
        "psql",
        "-U",
        user,
        "-d",
        db,
        "-At",
        "-F",
        "\t",
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        sql,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout


def run_psql_script(container: str, user: str, db: str, sql: str) -> None:
    cmd = [
        "docker",
        "exec",
        "-i",
        container,
        "psql",
        "-U",
        user,
        "-d",
        db,
        "-v",
        "ON_ERROR_STOP=1",
    ]
    subprocess.run(cmd, input=sql, text=True, check=True)


def load_csv(path: str) -> Dict[str, Dict[str, str]]:
    by_subject: Dict[str, Dict[str, str]] = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as file_obj:
        reader = csv.DictReader(file_obj)
        for row in reader:
            sid = (row.get("subject_id") or row.get("ptid") or row.get("PTID") or "").strip()
            if not sid:
                continue
            by_subject[sid] = row
    return by_subject


def get_db_patients(container: str, user: str, db: str) -> Tuple[Tuple[int, str], ...]:
    out = run_psql_query(
        container,
        user,
        db,
        "SELECT user_id, subject_id FROM patients WHERE subject_id IS NOT NULL AND subject_id <> '' ORDER BY user_id",
    )
    rows = []
    for line in out.splitlines():
        if not line.strip():
            continue
        user_id_str, subject_id = line.split("\t", 1)
        rows.append((int(user_id_str), subject_id))
    return tuple(rows)


def build_backfill_sql(user_id: int, row: Dict[str, str]) -> str:
    apoe4 = parse_int(row.get("apoe4"))
    pteducat = parse_int(row.get("pteducat"))
    cdr_sb = parse_float(row.get("cdr_sb"))
    nxaudito = parse_int(row.get("nxaudito"))

    # LDELTOTAL is the requested feature. Fall back to AVDELTOT if absent.
    ldeltotal_or_avdeltot = parse_float(row.get("ldeltotal"))
    if ldeltotal_or_avdeltot is None:
        ldeltotal_or_avdeltot = parse_float(row.get("AVDELTOT"))
    if ldeltotal_or_avdeltot is None:
        ldeltotal_or_avdeltot = parse_float(row.get("avdeltot"))

    return f"""
UPDATE patients
SET apoe4 = COALESCE({sql_num(apoe4)}, apoe4),
    pteducat = COALESCE({sql_num(pteducat)}, pteducat),
    updated_at = NOW()
WHERE user_id = {user_id};

WITH latest_ca AS (
  SELECT assessment_id
  FROM clinical_assessments
  WHERE patient_id = {user_id}
  ORDER BY exam_date DESC NULLS LAST, created_at DESC
  LIMIT 1
)
UPDATE clinical_assessments ca
SET cdr_sb = COALESCE({sql_num(cdr_sb)}, ca.cdr_sb),
    nxaudito = COALESCE({sql_num(nxaudito)}, ca.nxaudito)
WHERE ca.assessment_id IN (SELECT assessment_id FROM latest_ca);

WITH latest_nt AS (
  SELECT test_id
  FROM neuropsych_tests
  WHERE patient_id = {user_id}
  ORDER BY exam_date DESC NULLS LAST, created_at DESC
  LIMIT 1
)
UPDATE neuropsych_tests nt
SET avdeltot = COALESCE({sql_num(ldeltotal_or_avdeltot)}, nt.avdeltot)
WHERE nt.test_id IN (SELECT test_id FROM latest_nt);
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill DB fields from ADNI CSV by subject_id match")
    parser.add_argument(
        "--csv",
        default=os.path.join(os.getcwd(), "adni3_baseline_cohort_mciSP.csv"),
        help="Path to ADNI baseline CSV",
    )
    parser.add_argument("--container", default="mci-postgres", help="Postgres container name")
    parser.add_argument("--db-user", default="mci_user", help="Postgres user")
    parser.add_argument("--db-name", default="cognitive", help="Postgres database")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"[ERROR] CSV not found: {args.csv}")
        return 1

    csv_rows = load_csv(args.csv)
    if not csv_rows:
        print("[ERROR] CSV loaded but no rows with subject_id/PTID were found")
        return 1

    patients = get_db_patients(args.container, args.db_user, args.db_name)
    if not patients:
        print("[WARN] No patients with subject_id found in DB")
        return 0

    statements = ["BEGIN;"]
    matched = 0
    unmatched = 0
    for user_id, subject_id in patients:
        row = csv_rows.get(subject_id)
        if row is None:
            unmatched += 1
            continue
        matched += 1
        statements.append(build_backfill_sql(user_id, row))
    statements.append("COMMIT;")

    if matched == 0:
        print("[WARN] No DB patients matched CSV subject_id rows")
        return 0

    sql = "\n".join(statements)
    run_psql_script(args.container, args.db_user, args.db_name, sql)
    print(f"[OK] Backfill complete: matched={matched}, unmatched={unmatched}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
