import os
import re
import requests
import pymysql
import logging
from dotenv import load_dotenv
from datetime import datetime

# 환경 변수 로드
load_dotenv()

# FAISS 검색 API URL
FAISS_SEARCH_URL = os.getenv("FAISS_SEARCH_URL", "http://localhost:5000/search")

# DB 설정
DB_CONFIG = {
    "host": os.getenv("EMBED_DB_HOST"),
    "user": os.getenv("EMBED_DB_USER"),
    "password": os.getenv("EMBED_DB_PASSWORD"),
    "database": os.getenv("EMBEDDING_DATABASE_NAME"),
    "port": int(os.getenv("EMBED_DB_PORT", 3306)),
    "charset": "utf8mb4"
}

# 로그 파일 설정
logging.basicConfig(filename='faiss_failed_queries.log', level=logging.WARNING, encoding='utf-8')



def search_faiss_job_ids(query: str, top_k: int = 3):
    """
    FAISS 검색 API를 호출하여 유사도 기반 job_id 리스트를 반환
    """
    payload = {"query": query, "top_k": top_k}
    try:
        response = requests.post(FAISS_SEARCH_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        
        # API 응답 구조 확인을 위한 디버그
        print(f"DEBUG: API 응답 데이터: {data}")
        
        results = data.get("results", [])
        
        # 만약 results가 단순 int 리스트라면
        if results and isinstance(results[0], int):
            return [{"job_id": job_id, "similarity_score": 0.0} for job_id in results]
        
        # 이미 dict 형태라면 그대로 반환
        return results
        
    except requests.exceptions.RequestException as e:
        logging.warning(f"[{datetime.now()}] 검색 실패 query: {query}\n오류: {str(e)}\n")
        return []


def get_job_details_from_ids(job_ids):
    """
    job_id 리스트를 기반으로 MySQL에서 상세 채용공고 정보 조회
    """
    if not job_ids:
        return []

    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            placeholders = ','.join(['%s'] * len(job_ids))
            query = f"""
                SELECT job_id, position_title, description, posted_at
                FROM JobPosting
                WHERE job_id IN ({placeholders})
            """
            cursor.execute(query, job_ids)
            rows = cursor.fetchall()

            # 결과를 dict 리스트로 변환
            return [
                {
                    "job_id": row[0],
                    "position_title": row[1],
                    "description": row[2],
                    "posted_at": row[3].isoformat() if row[3] else None
                }
                for row in rows
            ]
    except Exception as e:
        logging.warning(f"[{datetime.now()}] DB 조회 실패 job_ids: {job_ids}\n오류: {str(e)}\n")
        return []
    finally:
        if 'connection' in locals() and connection:
            connection.close()