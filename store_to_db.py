import os
import pymysql
import json
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# DB 설정
DB_CONFIG = {
    "host": os.getenv("EMBED_DB_HOST"),
    "user": os.getenv("EMBED_DB_USER"),
    "password": os.getenv("EMBED_DB_PASSWORD"),
    "database": os.getenv("USER_DATABASE_NAME"),
    "port": int(os.getenv("EMBED_DB_PORT", 3306)),
    "charset": "utf8mb4"
}

def insert_to_database(user_id, blob_url, summary, skills, category, job_recommendations):
    """
    분석 결과를 기존 테이블 구조에 맞춰 데이터베이스에 저장
    """
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Resume 테이블에 삽입 (기존 구조에 맞춤)
            # parsed_json에 분석 결과를 JSON으로 저장
            analysis_data = {
                "summary": summary,
                "skills": skills if isinstance(skills, list) else [skills] if skills else [],
                "category": category,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            resume_query = """
                INSERT INTO Resume (user_id, file_path, blob_url, parsed_json, uploaded_at)
                VALUES (%s, %s, %s, %s, %s)
            """
            
            # file_path는 임시로 blob_url과 동일하게 설정 (기존 구조상 NOT NULL)
            file_path = blob_url if blob_url else f"resume_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            cursor.execute(resume_query, (
                user_id, 
                file_path,
                blob_url, 
                json.dumps(analysis_data, ensure_ascii=False),
                datetime.now()
            ))
            
            resume_id = cursor.lastrowid
            
            # JobRecommendation 테이블에 삽입 (기존 구조에 맞춤)
            if job_recommendations:
                recommendation_query = """
                    INSERT INTO JobRecommendation (user_id, resume_id, job_id, score, recommended_at)
                    VALUES (%s, %s, %s, %s, %s)
                """
                
                for job in job_recommendations:
                    if isinstance(job, dict):
                        job_id = job.get('job_id')
                        # similarity_score를 score 컬럼에 저장
                        score = job.get('similarity_score', 0.0)
                    else:
                        job_id = job
                        score = 0.0
                    
                    # job_id가 유효한 경우만 삽입
                    if job_id:
                        cursor.execute(recommendation_query, (
                            user_id,
                            resume_id, 
                            job_id, 
                            score, 
                            datetime.now()
                        ))
            
            connection.commit()
            print(f"  Resume 저장 완료: ID {resume_id}")
            print(f"  추천 결과 {len(job_recommendations) if job_recommendations else 0}개 저장 완료")
            return resume_id
            
    except Exception as e:
        print(f"DB 저장 중 오류 발생: {str(e)}")
        if 'connection' in locals():
            connection.rollback()
        raise
    finally:
        if 'connection' in locals() and connection:
            connection.close()