import os
import psycopg2
import sys

def get_db_connection():
    # README.md 설정에 맞춘 DB 연결 정보
    dsn = os.getenv("DATABASE_URL", "postgresql://mci_user:change_me@postgres:5432/cognitive")
    return psycopg2.connect(dsn)

def main():
    print("🔍 DB와 MinIO(파일시스템) 매칭 확인 중...")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # MRI 평가 기록과 환자 정보 조회
        query = """
            SELECT 
                ma.assessment_id,
                p.subject_id,
                ma.file_path,
                ma.classification,
                ma.confidence,
                ma.probabilities,
                ma.preprocessing_status
            FROM mri_assessments ma
            JOIN patients p ON ma.patient_id = p.user_id
            ORDER BY ma.created_at DESC
        """
        cur.execute(query)
        rows = cur.fetchall()
        
        if not rows:
            print("⚠️ DB에 MRI 분석 기록이 없습니다.")
            return

        print(f"총 {len(rows)}개의 MRI 기록을 확인합니다.\n")
        
        for row in rows:
            assessment_id, subject_id, file_path, classification, confidence, probabilities, status = row
            
            print(f"🆔 Assessment ID: {assessment_id}")
            print(f"👤 Subject ID: {subject_id}")
            print(f"📂 DB File Path: {file_path}")
            print(f"⚙️ Status: {status}")
            
            # 파일 존재 여부 확인
            if file_path and os.path.exists(file_path):
                print("✅ [파일 시스템] 파일이 존재합니다.")
                
                # 파일명에 Subject ID가 포함되어 있는지 확인 (매칭 검증)
                if subject_id in os.path.basename(file_path):
                    print("✅ [ID 매칭] 파일명에 Subject ID가 올바르게 포함되어 있습니다.")
                else:
                    print(f"⚠️ [ID 매칭 경고] 파일명({os.path.basename(file_path)})에 Subject ID({subject_id})가 없습니다.")
            else:
                print(f"❌ [파일 시스템] 파일을 찾을 수 없습니다! (경로 확인 필요)")
                if file_path and file_path.startswith("/srv"):
                    print("   💡 팁: 컨테이너 내부에 호스트 경로(/srv/...)가 마운트되어 있는지 확인하세요.")
                
            print(f"📊 결과: {classification} (Confidence: {confidence})")
            print(f"📈 확률 분포: {probabilities}")
            print("-" * 50)

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    main()