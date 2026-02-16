import os
import psycopg2
import glob

def main():
    print("🔍 데이터 삭제 및 시스템 상태 확인 중...")
    
    # 1. DB 확인
    try:
        # tasks.py와 동일한 DB 연결 설정 사용
        dsn = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/mci")
        conn = psycopg2.connect(dsn, options="-c timezone=Asia/Seoul")
        cur = conn.cursor()
        
        # MRI 테이블 레코드 수 확인
        cur.execute("SELECT count(*) FROM mri_assessments")
        mri_cnt = cur.fetchone()[0]
        print(f"   [DB] mri_assessments 레코드 수: {mri_cnt} (0이어야 정상)")
        
        # 101번 환자 존재 여부 확인
        cur.execute("SELECT user_id, name FROM users WHERE user_id = 101")
        user_101 = cur.fetchone()
        if user_101:
            print(f"   [DB] ⚠️ 101번 환자(테스트환자)가 아직 DB에 남아있습니다: {user_101}")
        else:
            print("   [DB] ✅ 101번 환자가 DB에 존재하지 않습니다.")
            
        conn.close()
    except Exception as e:
        print(f"   [DB] ❌ 연결 실패: {e}")

    # 2. 파일 시스템 확인
    # MinIO 데이터 폴더 내의 모든 .nii / .nii.gz 파일 검색
    base_dir = "/srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final/minio-data"
    files = glob.glob(f"{base_dir}/**/*.nii*", recursive=True)
    
    # 템플릿 파일(templates 폴더)은 제외하고 실제 데이터만 필터링
    data_files = [f for f in files if "templates" not in f]
    
    if not data_files:
        print("   [File] ✅ 디스크에 잔여 MRI 파일이 없습니다.")
    else:
        print(f"   [File] ⚠️ {len(data_files)}개의 MRI 파일이 발견되었습니다 (삭제 필요):")
        for f in data_files[:3]:
            print(f"      - {f}")

if __name__ == "__main__":
    main()
