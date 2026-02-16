import os
import sys
import time
import psycopg2
from uuid import uuid4
from celery import Celery

# Celery Setup
app = Celery(
    'mci-worker',
    broker=os.getenv('REDIS_URL', 'redis://redis:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://redis:6379/0')
)

def get_db_connection():
    # Default to README settings if env var is missing
    dsn = os.getenv("DATABASE_URL", "postgresql://mci_user:change_me@postgres:5432/cognitive")
    return psycopg2.connect(dsn, options="-c timezone=Asia/Seoul")

def main():
    print("🚀 Pipeline Trigger Starting...")
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Check Patient (Hong Gil-dong, user_id=100)
        print("1️⃣  Checking Patient (ID: 100)...")
        cur.execute("SELECT subject_id FROM patients WHERE user_id = 100")
        row = cur.fetchone()
        if not row:
            print("   ❌ Patient 100 not found.")
            print("   👉 Please run the SQL script first: migrations/006_insert_dummy_data.sql")
            return
        
        subject_id = row[0]
        print(f"   ✅ Found Patient: Hong Gil-dong (Subject ID: {subject_id})")
        
        # 2. Verify Preprocessed File Exists
        # Using the path defined in tasks.py
        candidates = [
            "/srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final/minio-data/processed",
            "/app/minio-data/processed"
        ]
        preprocessed_dir = candidates[0]
        for p in candidates:
            if os.path.exists(p):
                preprocessed_dir = p
                break

        found_file = False
        if os.path.exists(preprocessed_dir):
            for f in os.listdir(preprocessed_dir):
                if subject_id in f and f.endswith('.nii.gz'):
                    print(f"   ✅ Verified preprocessed file on disk: {f}")
                    found_file = True
                    break
        else:
            print(f"   ⚠️  Directory not found inside container: {preprocessed_dir}")
        
        if not found_file:
            print(f"   ⚠️  Warning: No preprocessed file found for '{subject_id}' in {preprocessed_dir}")
            print("      The worker will attempt to preprocess from scratch.")

        # 3. Create MRI Assessment Record
        print("2️⃣  Creating MRI Assessment Record...")
        assessment_id = str(uuid4())
        dummy_raw_path = f"mri-scans/{subject_id}/dummy_trigger.dcm"
        
        cur.execute("""
            INSERT INTO mri_assessments 
            (assessment_id, patient_id, file_path, scan_date, classification, confidence, preprocessing_status, created_at)
            VALUES (%s, %s, %s, NOW(), 'pending', 0.0, 'pending', NOW())
        """, (assessment_id, 100, dummy_raw_path))
        conn.commit()
        print(f"   ✅ Created Assessment ID: {assessment_id}")
        
        # 4. Trigger Celery Task
        print("3️⃣  Sending Task to Celery...")
        task = app.send_task(
            'process_mri_scan',
            args=[assessment_id, "100", dummy_raw_path]
        )
        print(f"   ✅ Task Sent! Task ID: {task.id}")
        
        # 5. Wait for Result
        print("4️⃣  Waiting for Worker Result (timeout=60s)...")
        try:
            result = task.get(timeout=60)
            print("\n🎉 Analysis Complete!")
            print(f"   Result: {result.get('result')}")
            print(f"   Confidence: {result.get('confidence'):.4f}")
        except Exception as e:
            print(f"\n⚠️  Task wait failed (timeout or error): {e}")
            print("   Check worker logs for details.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
