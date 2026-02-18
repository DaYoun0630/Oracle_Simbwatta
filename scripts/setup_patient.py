import csv
import glob
import os
import re
from datetime import date

import psycopg2


TARGET_SUBJECT_ID = "029_S_6726"


def find_base_path():
    candidates = [
        "/srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final",
        "/app",
        os.getcwd(),
    ]
    for base in candidates:
        if os.path.exists(os.path.join(base, "minio-data/processed")):
            return base
    return candidates[0]


BASE_PATH = find_base_path()
PROCESSED_DIR = os.path.join(BASE_PATH, "minio-data/processed")
CSV_PATH = os.path.join(BASE_PATH, "adni3_baseline_cohort_mciSP.csv")


def get_db_connection():
    dsn = os.getenv("DATABASE_URL", "postgresql://mci_user:change_me1@postgres:5432/cognitive")
    return psycopg2.connect(dsn, options="-c timezone=Asia/Seoul")


def _normalize_key(key):
    if key is None:
        return ""
    return str(key).replace("\ufeff", "").strip().lower()


def _normalize_row(row):
    normalized = {}
    for key, value in row.items():
        normalized_key = _normalize_key(key)
        if not normalized_key:
            continue
        normalized[normalized_key] = value.strip() if isinstance(value, str) else value
    return normalized


def _to_int(value, default=None):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return default


def _to_float(value, default=None):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    try:
        return float(text)
    except (TypeError, ValueError):
        return default


def _to_date_str(value, default):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return default


def _map_risk_level(csv_data):
    diagnosis = _to_int(csv_data.get("diagnosis"))
    if diagnosis is not None:
        if diagnosis <= 1:
            return "low"
        if diagnosis == 2:
            return "mid"
        return "high"

    cdr_sb = _to_float(csv_data.get("cdr_sb"))
    if cdr_sb is None:
        return "low"
    if cdr_sb < 1.5:
        return "low"
    if cdr_sb < 4.0:
        return "mid"
    return "high"


def _map_mri_classification(csv_data):
    diagnosis = _to_int(csv_data.get("diagnosis"))
    if diagnosis is None:
        return "LMCI"
    if diagnosis <= 1:
        return "CN"
    if diagnosis == 2:
        return "LMCI"
    return "AD"


def find_mri_file():
    pattern = os.path.join(PROCESSED_DIR, "*.nii.gz")
    files = glob.glob(pattern)
    if not files:
        print(f"⚠️ No .nii.gz files found in {PROCESSED_DIR}; using default subject {TARGET_SUBJECT_ID}.")
        return TARGET_SUBJECT_ID, None

    file_path = files[0]
    file_name = os.path.basename(file_path)

    match = re.search(r"(\d{3}_S_\d{4})", file_name)
    if match:
        subject_id = match.group(1)
    else:
        subject_id = file_name.replace(".nii.gz", "").replace(".nii", "")

    print(f"📂 Found MRI File: {file_name}")
    print(f"🆔 Extracted Subject ID: {subject_id}")
    return subject_id, file_path


def read_csv_data(subject_id):
    if not os.path.exists(CSV_PATH):
        print(f"⚠️ CSV file not found at {CSV_PATH}. Using default dummy data.")
        return {}

    print(f"📖 Reading CSV: {CSV_PATH}")
    data = {}
    try:
        with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            for raw_row in reader:
                row = _normalize_row(raw_row)
                row_id = row.get("ptid") or row.get("subject") or row.get("subject_id")
                if row_id == subject_id:
                    data = row
                    break
    except Exception as exc:
        print(f"⚠️ Error reading CSV: {exc}")

    if data:
        print(f"✅ Found CSV data for {subject_id}")
    else:
        print(f"⚠️ Subject {subject_id} not found in CSV.")

    return data


def setup_database(subject_id, mri_path, csv_data):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        print("🔄 Cleaning up old data...")
        cur.execute(
            "TRUNCATE TABLE voice_assessments, recordings, training_sessions, mri_assessments, "
            "neuropsych_tests, visits, biomarkers, clinical_assessments, patients, doctor, users CASCADE;"
        )

        print("👤 Creating Users (Doctor & Patient)...")
        cur.execute(
            """
            INSERT INTO users (user_id, email, name, oauth_provider_id, created_at, updated_at) VALUES
            (1, 'doctor@mci.com', 'Dr. Kim', 'google-doc-1', NOW(), NOW()),
            (100, 'patient@mci.com', '김성신', 'google-pat-1', NOW(), NOW());
            """
        )
        cur.execute("SELECT setval('users_user_id_seq', (SELECT MAX(user_id) FROM users));")
        cur.execute("INSERT INTO doctor (user_id, hospital, license_number) VALUES (1, '서울대학교병원', 'MD-12345');")

        # Defaults: used only when CSV row is missing.
        rid = 1234
        date_of_birth = "1950-01-01"
        gender = 1
        pteducat = None
        apoe4 = None
        risk_level = "low"
        exam_date = date.today().isoformat()
        viscode2 = "bl"
        image_id = 123457
        origprot = "ADNI3"
        colprot = "ADNI3"
        mmse = 26
        moca = 24.0
        adas_cog13 = 15.0
        cdr_global = 0.5
        cdr_memory = 0.5
        cdr_sb = 2.0
        faq = 5.0
        gds = None
        cci = None
        nxaudito = None
        avtot1 = avtot2 = avtot3 = avtot4 = avtot5 = avtot6 = avtotb = None
        avdel30min = avdeltot = averr1 = averr2 = None
        ravlt_immediate = ravlt_learning = ravlt_forgetting = ravlt_pct_forgetting = None
        traascor = trabscor = None
        abeta42 = 450.0
        abeta40 = 1000.0
        ptau = 25.0
        tau = 350.0
        ab42_ab40 = None
        ptau_ab42 = None
        ttau_ab42 = None
        mri_classification = "LMCI"

        if csv_data and (csv_data.get("subject_id") == subject_id == TARGET_SUBJECT_ID):
            rid = _to_int(csv_data.get("rid"), rid)
            date_of_birth = _to_date_str(csv_data.get("ptdobyy"), date_of_birth)
            gender = _to_int(csv_data.get("gender"), gender)
            pteducat = _to_int(csv_data.get("pteducat"), pteducat)
            apoe4 = _to_int(csv_data.get("apoe4"))
            risk_level = _map_risk_level(csv_data)
            exam_date = _to_date_str(csv_data.get("examdate"), exam_date)
            viscode2 = str(csv_data.get("viscode2") or viscode2).strip().lower()
            image_id = _to_int(csv_data.get("image_id"), image_id)
            origprot = str(csv_data.get("origprot") or origprot).strip()
            colprot = str(csv_data.get("colprot") or colprot).strip()
            mmse = _to_int(csv_data.get("mmse"), mmse)
            moca = _to_float(csv_data.get("moca"), moca)
            adas_cog13 = _to_float(csv_data.get("adas_cog13"), adas_cog13)
            cdr_global = _to_float(csv_data.get("cdr_global"), cdr_global)
            cdr_memory = _to_float(csv_data.get("cdr_memory"), cdr_memory)
            cdr_sb = _to_float(csv_data.get("cdr_sb"), cdr_sb)
            faq = _to_float(csv_data.get("faq"), faq)
            gds = _to_float(csv_data.get("gds"))
            cci = _to_float(csv_data.get("cci"))
            nxaudito = _to_int(csv_data.get("nxaudito"))
            avtot1 = _to_float(csv_data.get("avtot1"))
            avtot2 = _to_float(csv_data.get("avtot2"))
            avtot3 = _to_float(csv_data.get("avtot3"))
            avtot4 = _to_float(csv_data.get("avtot4"))
            avtot5 = _to_float(csv_data.get("avtot5"))
            avtot6 = _to_float(csv_data.get("avtot6"))
            avtotb = _to_float(csv_data.get("avtotb"))
            avdel30min = _to_float(csv_data.get("avdel30min"))
            avdeltot = _to_float(csv_data.get("ldeltotal"))
            if avdeltot is None:
                avdeltot = _to_float(csv_data.get("avdeltot"))
            averr1 = _to_float(csv_data.get("averr1"))
            averr2 = _to_float(csv_data.get("averr2"))
            ravlt_immediate = _to_float(csv_data.get("ravlt_immediate"))
            ravlt_learning = _to_float(csv_data.get("ravlt_learning"))
            ravlt_forgetting = _to_float(csv_data.get("ravlt_forgetting"))
            ravlt_pct_forgetting = _to_float(csv_data.get("ravlt_pct_forgetting"))
            traascor = _to_float(csv_data.get("traascor"))
            trabscor = _to_float(csv_data.get("trabscor"))
            abeta42 = _to_float(csv_data.get("abeta42"), abeta42)
            abeta40 = _to_float(csv_data.get("abeta40"), abeta40)
            ptau = _to_float(csv_data.get("ptau"), ptau)
            tau = _to_float(csv_data.get("tau"), tau)
            ab42_ab40 = _to_float(csv_data.get("ab42/ab40"))
            ptau_ab42 = _to_float(csv_data.get("ptau/ab42"))
            ttau_ab42 = _to_float(csv_data.get("ttau/ab42"))
            mri_classification = _map_mri_classification(csv_data)
            print("✅ CSV matched (029_S_6726): loading patient features from CSV columns.")
        else:
            print("⚠️ CSV match not found for target subject. Loading fallback defaults.")

        print(f"   - Patient: 김성신 (ID: 100, Subject: {subject_id})")
        cur.execute(
            """
            INSERT INTO patients (
                user_id, doctor_id, date_of_birth, gender, pteducat, apoe4, risk_level, rid, subject_id, created_at, updated_at
            ) VALUES (100, 1, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW());
            """,
            (date_of_birth, gender, pteducat, apoe4, risk_level, rid, subject_id),
        )

        visit_id = "55555555-5555-5555-5555-555555555555"
        cur.execute(
            """
            INSERT INTO visits (visit_id, patient_id, exam_date, viscode2, image_id, origprot, colprot, created_at)
            VALUES (%s, 100, %s, %s, %s, %s, %s, NOW());
            """,
            (visit_id, exam_date, viscode2, image_id, origprot, colprot),
        )

        cur.execute(
            """
            INSERT INTO clinical_assessments (
                assessment_id, visit_id, patient_id, exam_date, viscode2, mmse, moca, adas_cog13,
                cdr_global, cdr_memory, cdr_sb, faq, gds, cci, nxaudito, created_at
            ) VALUES (gen_random_uuid(), %s, 100, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW());
            """,
            (
                visit_id,
                exam_date,
                viscode2,
                mmse,
                moca,
                adas_cog13,
                cdr_global,
                cdr_memory,
                cdr_sb,
                faq,
                gds,
                cci,
                nxaudito,
            ),
        )

        cur.execute(
            """
            INSERT INTO neuropsych_tests (
                test_id, visit_id, patient_id, exam_date, viscode2,
                avtot1, avtot2, avtot3, avtot4, avtot5, avtot6, avtotb,
                avdel30min, avdeltot, averr1, averr2,
                ravlt_immediate, ravlt_learning, ravlt_forgetting, ravlt_pct_forgetting,
                traascor, trabscor, created_at
            ) VALUES (
                gen_random_uuid(), %s, 100, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, NOW()
            );
            """,
            (
                visit_id,
                exam_date,
                viscode2,
                avtot1,
                avtot2,
                avtot3,
                avtot4,
                avtot5,
                avtot6,
                avtotb,
                avdel30min,
                avdeltot,
                averr1,
                averr2,
                ravlt_immediate,
                ravlt_learning,
                ravlt_forgetting,
                ravlt_pct_forgetting,
                traascor,
                trabscor,
            ),
        )

        cur.execute(
            """
            INSERT INTO biomarkers (
                biomarker_id, visit_id, patient_id, collected_date, abeta42, abeta40, ptau, tau,
                ab42_ab40, ptau_ab42, ttau_ab42, created_at
            ) VALUES (gen_random_uuid(), %s, 100, %s, %s, %s, %s, %s, %s, %s, %s, NOW());
            """,
            (
                visit_id,
                exam_date,
                abeta42,
                abeta40,
                ptau,
                tau,
                ab42_ab40,
                ptau_ab42,
                ttau_ab42,
            ),
        )

        raw_file_path = mri_path or f"mri/{subject_id}.nii.gz"
        cur.execute(
            """
            INSERT INTO mri_assessments (assessment_id, patient_id, image_id, file_path, scan_date, classification, confidence, created_at)
            VALUES (gen_random_uuid(), 100, %s, %s, %s, %s, 0.85, NOW());
            """,
            (image_id, raw_file_path, exam_date, mri_classification),
        )

        cur.execute(
            """
            INSERT INTO training_sessions (training_id, patient_id, started_at, ended_at, exercise_type) VALUES
            ('66666666-6666-6666-6666-666666666666', 100, NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days' + INTERVAL '10 minutes', 'daily_conversation');
            """
        )
        cur.execute(
            """
            INSERT INTO recordings (recording_id, training_id, patient_id, file_path, duration_seconds, recorded_at, status) VALUES
            ('77777777-7777-7777-7777-777777777777', '66666666-6666-6666-6666-666666666666', 100, 'voice/sample1.wav', 60, NOW() - INTERVAL '2 days', 'completed');
            """
        )
        cur.execute(
            """
            INSERT INTO voice_assessments (assessment_id, recording_id, assessed_at, cognitive_score, mci_probability, flag, transcript) VALUES
            (gen_random_uuid(), '77777777-7777-7777-7777-777777777777', NOW() - INTERVAL '2 days', 75, 0.4, 'normal', '안녕하세요. 오늘 날씨가 참 좋네요.');
            """
        )

        conn.commit()
        print("✅ Database updated successfully.")

    except Exception as exc:
        conn.rollback()
        print(f"❌ Database Error: {exc}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    sid, mpath = find_mri_file()
    cdata = read_csv_data(sid)
    setup_database(sid, mpath, cdata)
