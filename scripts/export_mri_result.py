import os
import sys
import json
import psycopg2
from datetime import datetime

def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def export_latest_result(output_file="mri_analysis_result.json"):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # 가장 최근에 완료된 MRI 분석 결과 조회
        cur.execute("""
            SELECT 
                ma.assessment_id,
                p.subject_id,
                ma.classification,
                ma.confidence,
                ma.probabilities,
                ma.file_path,
                ma.processed_at
            FROM mri_assessments ma
            JOIN patients p ON ma.patient_id = p.user_id
            WHERE ma.preprocessing_status = 'completed'
            ORDER BY ma.processed_at DESC
            LIMIT 1
        """)
        
        row = cur.fetchone()
        
        if not row:
            print("❌ 완료된 MRI 분석 결과가 없습니다.")
            return

        result = {
            "assessment_id": str(row[0]),
            "subject_id": row[1],
            "prediction": row[2],
            "confidence": float(row[3]),
            "probabilities": row[4],
            "file_path": row[5],
            "processed_at": row[6].isoformat() if row[6] else None,
            "exported_at": datetime.now().isoformat()
        }

        # JSON 파일로 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
            
        print(f"✅ 분석 결과가 저장되었습니다: {output_file}")
        print(json.dumps(result, indent=4, ensure_ascii=False))

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else "mri_analysis_result.json"
    export_latest_result(output_path)