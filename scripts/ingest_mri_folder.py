import os
import sys
import psycopg2
import re
import socket
import subprocess
import argparse
from uuid import uuid4
from celery import Celery

# Celery 설정 (Redis 연결)
celery_app = Celery(
    'mci-worker',
    broker=os.getenv('REDIS_URL', 'redis://redis:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://redis:6379/0')
)

def get_db_connection():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        # Host-side default (compose publishes postgres on localhost:5432)
        dsn = "postgresql://mci_user:change_me1@localhost:5432/cognitive"
    return psycopg2.connect(dsn, options="-c timezone=Asia/Seoul")


def _host_resolves(hostname: str) -> bool:
    try:
        socket.gethostbyname(hostname)
        return True
    except Exception:
        return False


def _is_container_running(name: str) -> bool:
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", name],
            check=False,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0 and result.stdout.strip().lower() == "true"
    except Exception:
        return False


def _send_task_via_worker_container(task_name: str, args: list[str]) -> str:
    """
    Fallback dispatch path when host shell cannot resolve internal compose services
    (e.g., redis://redis:6379). Sends Celery task from inside mci-worker container.
    """
    if not _is_container_running("mci-worker"):
        raise RuntimeError("Fallback failed: container 'mci-worker' is not running.")

    pycode = (
        "from celery import Celery;"
        "import os;"
        "app=Celery('mci-worker',"
        "broker=os.getenv('REDIS_URL','redis://redis:6379/0'),"
        "backend=os.getenv('REDIS_URL','redis://redis:6379/0'));"
        f"t=app.send_task({task_name!r}, args={args!r});"
        "print(t.id)"
    )

    result = subprocess.run(
        ["docker", "exec", "mci-worker", "/app/.venv/bin/python", "-c", pycode],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Fallback dispatch via mci-worker failed.\n"
            f"stdout: {result.stdout.strip()}\n"
            f"stderr: {result.stderr.strip()}"
        )

    task_id = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    if not task_id:
        raise RuntimeError("Fallback dispatch succeeded but task id was not returned.")
    return task_id


DEFAULT_MRI_FOLDER_PATH = os.getenv(
    "MRI_INGEST_DEFAULT_PATH",
    "/srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final/data/raw/mri/029_S_6726",
)


def extract_subject_id(path: str) -> str:
    """Extract ADNI-like subject ID (e.g., 002_S_0559) from any path."""
    match = re.search(r"\d{3}_S_\d{4}", path or "")
    if match:
        return match.group(0)
    return os.path.basename((path or "").rstrip("/"))

def ingest_mri(folder_path, patient_id_override: str | None = None):
    # MinIO object/prefix path passthrough
    if folder_path.startswith("s3://") or folder_path.startswith("mri-scans/"):
        source_path = folder_path
        subject_id = extract_subject_id(folder_path)
    else:
        source_path = None
        subject_id = None

    # 1. 경로 보정 (Host 경로 -> Docker 내부 경로)
    # 호스트 경로(/srv/...)가 들어오면 컨테이너 경로(/app/...)로 변환
    container_path = folder_path
    host_prefix = "/srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final"
    
    if folder_path.startswith(host_prefix):
        container_path = folder_path.replace(host_prefix, "/app")

    # 2. source path / subject id 계산
    # - MinIO MRI 디렉터리 경로는 mri-scans/<prefix> 형태로 저장
    # - 그 외는 기존 컨테이너 경로 유지
    if source_path is None:
        if "/minio-data/mri-scans/" in folder_path:
            source_path = "mri-scans/" + folder_path.split("/minio-data/mri-scans/", 1)[1].strip("/")
            subject_id = extract_subject_id(folder_path)
        elif "/minio-data/mri-scans/" in container_path:
            source_path = "mri-scans/" + container_path.split("/minio-data/mri-scans/", 1)[1].strip("/")
            subject_id = extract_subject_id(container_path)
        else:
            source_path = container_path
            subject_id = extract_subject_id(folder_path)
    
    print(f"📂 Processing Folder: {subject_id}")
    print(f"   - Host Path: {folder_path}")
    print(f"   - Container Path: {container_path}")
    print(f"   - Stored Source Path: {source_path}")

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # 3. 환자 조회
        if patient_id_override is not None:
            cur.execute("SELECT user_id, subject_id FROM patients WHERE user_id = %s", (patient_id_override,))
            row = cur.fetchone()
            if not row:
                print(f"❌ Error: Patient with user_id '{patient_id_override}' not found in DB.")
                return
            patient_id = row[0]
            db_subject_id = row[1]
            if not subject_id and db_subject_id:
                subject_id = str(db_subject_id)
            print(f"✅ Using explicit Patient ID: {patient_id}")
        else:
            cur.execute("SELECT user_id FROM patients WHERE subject_id = %s", (subject_id,))
            row = cur.fetchone()
            if not row:
                print(f"❌ Error: Patient with subject_id '{subject_id}' not found in DB.")
                print("   -> Pass --patient-id to target a specific user.")
                return
            patient_id = row[0]
            print(f"✅ Found Patient ID: {patient_id}")
        
        # 4. Assessment 레코드 생성 (UUID 발급)
        assessment_id = str(uuid4())
        
        # file_path와 scan_date 등을 초기화
        cur.execute("""
            INSERT INTO mri_assessments 
            (assessment_id, patient_id, file_path, scan_date, classification, confidence, created_at)
            VALUES (
                %s,
                %s,
                %s,
                TIMEZONE('Asia/Seoul', NOW()),
                'pending',
                0.0,
                TIMEZONE('Asia/Seoul', NOW())
            )
        """, (assessment_id, patient_id, source_path))
        
        conn.commit()
        print(f"✅ Created DB Record: {assessment_id}")
        
        # 5. Celery Task 트리거
        # process_mri_scan(mri_id, patient_id, file_path)
        dispatch_args = [assessment_id, str(patient_id), source_path]
        # Host shell usually cannot resolve compose-internal host "redis".
        # In that case, skip slow retry path and use container fallback immediately.
        if not _host_resolves("redis"):
            print("ℹ️  Host cannot resolve internal 'redis' service. Using docker fallback...")
            task_id = _send_task_via_worker_container("process_mri_scan", dispatch_args)
            print("🚀 Celery Task Triggered via mci-worker container!")
            print(f"   - Task ID: {task_id}")
        else:
            try:
                task = celery_app.send_task('process_mri_scan', args=dispatch_args)
                print("🚀 Celery Task Triggered!")
                print(f"   - Task ID: {task.id}")
            except Exception as dispatch_err:
                print(f"⚠️  Host dispatch failed: {dispatch_err}")
                task_id = _send_task_via_worker_container("process_mri_scan", dispatch_args)
                print("🚀 Celery Task Triggered via mci-worker container!")
                print(f"   - Task ID: {task_id}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

def parse_args():
    parser = argparse.ArgumentParser(description="Ingest MRI folder/object and trigger worker pipeline.")
    parser.add_argument(
        "path",
        nargs="?",
        default=DEFAULT_MRI_FOLDER_PATH,
        help="MRI folder path or MinIO object/prefix path",
    )
    parser.add_argument(
        "--patient-id",
        dest="patient_id",
        default=None,
        help="Optional explicit patient user_id override (e.g., 109 for 오동군)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    target_path = args.path

    if not target_path:
        print("❌ Error: MRI path is empty.")
        sys.exit(1)

    ingest_mri(target_path, patient_id_override=args.patient_id)
