import os
import pymysql
import json
from datetime import datetime
from dotenv import load_dotenv
from resume_analysis import parse_resume_sections  # 🔥 GPT 평가 텍스트에서 강점/약점/개선점 파싱

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

def insert_to_database(
    user_id,
    blob_url,
    summary,
    skills,
    category,
    job_recommendations,
    search_query=None,
    cot_analyses=None
):
    """
    분석 결과를 Resume, ResumeEvalResult, JobRecommendation 테이블에 저장
    """
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # -----------------------------
            # 1. Resume 테이블 삽입
            # -----------------------------
            analysis_data = {
                "summary": summary,
                "skills": skills if isinstance(skills, list) else [skills] if skills else [],
                "category": category,
                "analysis_timestamp": datetime.now().isoformat()
            }

            file_path = blob_url or f"resume_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

            cursor.execute("""
                INSERT INTO Resume (user_id, file_path, blob_url, parsed_json, uploaded_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                user_id,
                file_path,
                blob_url,
                json.dumps(analysis_data, ensure_ascii=False),
                datetime.now()
            ))

            resume_id = cursor.lastrowid

            # -----------------------------
            # 2. ResumeEvalResult 테이블 삽입
            # -----------------------------
            strengths, weaknesses, improvement = parse_resume_sections(summary)

            cursor.execute("""
                INSERT INTO ResumeEvalResult (
                    resume_id, evaluation_summary, strengths, weaknesses, improvement,
                    skills_inferred, job_category_inferred, search_query
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                resume_id,
                summary,
                strengths,
                weaknesses,
                improvement,
                json.dumps(skills, ensure_ascii=False),
                category,
                search_query or ""
            ))

            # -----------------------------
            # 3. JobRecommendation 테이블 삽입
            # -----------------------------
            if job_recommendations:
                recommendation_query = """
                    INSERT INTO JobRecommendation (
                        user_id, resume_id, job_id, score, `rank`, recommended_reason, recommended_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """

                for rank, job in enumerate(job_recommendations, start=1):
                    if isinstance(job, dict):
                        job_id = job.get('job_id')
                        score = job.get('similarity_score', 0.0)
                    else:
                        job_id = job
                        score = 0.0

                    if job_id:
                        reason = cot_analyses[rank - 1] if cot_analyses and len(cot_analyses) >= rank else None
                        cursor.execute(recommendation_query, (
                            user_id,
                            resume_id,
                            job_id,
                            score,
                            rank,
                            reason,
                            datetime.now()
                        ))

            # -----------------------------
            # COMMIT & 반환
            # -----------------------------
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
