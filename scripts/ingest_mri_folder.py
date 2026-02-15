import os
import sys
import psycopg2
import re
from uuid import uuid4
from celery import Celery

# Celery 설정 (Redis 연결)
celery_app = Celery(
    'mci-worker',
    broker=os.getenv('REDIS_URL', 'redis://redis:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://redis:6379/0')
)

def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def extract_subject_id(path: str) -> str:
    """Extract ADNI-like subject ID (e.g., 002_S_0559) from any path."""
    match = re.search(r"\d{3}_S_\d{4}", path or "")
    if match:
        return match.group(0)
    return os.path.basename((path or "").rstrip("/"))

def ingest_mri(folder_path):
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
        
        # 3. 환자 조회 (Subject ID -> User ID)
        cur.execute("SELECT user_id FROM patients WHERE subject_id = %s", (subject_id,))
        row = cur.fetchone()
        
        if not row:
            print(f"❌ Error: Patient with subject_id '{subject_id}' not found in DB.")
            print("   -> Please register the patient first.")
            return
            
        patient_id = row[0]
        print(f"✅ Found Patient ID: {patient_id}")
        
        # 4. Assessment 레코드 생성 (UUID 발급)
        assessment_id = str(uuid4())
        
        # file_path와 scan_date 등을 초기화
        cur.execute("""
            INSERT INTO mri_assessments 
            (assessment_id, patient_id, file_path, scan_date, classification, confidence, created_at)
            VALUES (%s, %s, %s, NOW(), 'pending', 0.0, NOW())
        """, (assessment_id, patient_id, source_path))
        
        conn.commit()
        print(f"✅ Created DB Record: {assessment_id}")
        
        # 5. Celery Task 트리거
        # process_mri_scan(mri_id, patient_id, file_path)
        celery_app.send_task(
            'process_mri_scan',
            args=[assessment_id, str(patient_id), source_path]
        )
        print("🚀 Celery Task Triggered!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest_mri_folder.py <path_to_mri_folder>")
        sys.exit(1)
        
    ingest_mri(sys.argv[1])
