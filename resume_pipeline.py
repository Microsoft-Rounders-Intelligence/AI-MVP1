import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from upload_to_blob import upload_pdf_to_blob
from resume_analysis import (
    extract_text_from_pdf,
    evaluate_resume,
    extract_skills_and_category,
    generate_query_from_report,
)
from recommend_jobs_from_faiss import search_faiss_job_ids, get_job_details_from_ids
from store_to_db import insert_to_database

# 프롬프트 모듈 로드
from prompts import COT_ANALYSIS_PROMPT_TEMPLATE

# 환경 변수 로드
load_dotenv()

# Azure OpenAI 클라이언트 설정 (🔁 .env 기준 반영)
client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version="2024-02-15-preview",
    azure_endpoint=os.getenv("OPENAI_ENDPOINT")
)

def generate_cot_analysis(user_skills, user_category, job_description, job_title, similarity_score, search_query):
    """
    GPT를 사용하여 추천 이유를 CoT 방식으로 분석
    """
    formatted_skills = ", ".join(user_skills) if user_skills else "정보 없음"

    prompt = COT_ANALYSIS_PROMPT_TEMPLATE.format(
        user_category=user_category or "정보 없음",
        user_skills=formatted_skills,
        search_query=search_query,
        job_title=job_title,
        similarity_score=similarity_score,
        job_description=job_description[:1000]
    )

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_DEPLOYMENT", "gpt-4"),
            messages=[
                {"role": "system", "content": "당신은 채용공고 추천 시스템의 전문 분석가입니다. 객관적이고 논리적인 분석을 제공합니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"GPT 분석 생성 중 오류 발생: {str(e)}"


def run_pipeline(user_id, pdf_path):
    print("\n이력서 자동 분석 파이프라인 시작\n")

    # 1. Azure Blob 업로드
    print("[1] Azure Blob 업로드 시작...")
    blob_url = upload_pdf_to_blob(pdf_path, user_id)
    print(f"  업로드 완료. Blob URL: {blob_url}")

    # 2. PDF 텍스트 추출
    print("\n[2] 이력서에서 텍스트 추출 중...")
    text = extract_text_from_pdf(pdf_path)
    print("  텍스트 추출 완료")
    print("  추출 텍스트 (앞 500자):\n", text[:500], "\n...")

    # 3. GPT 이력서 평가
    print("\n[3] GPT 기반 이력서 평가 중...")
    summary = evaluate_resume(text)
    print("  평가 완료")
    print("  평가 요약:\n", summary[:700], "\n...")

    # 4. 기술스택/카테고리 추출 및 쿼리 생성
    print("\n[4] 기술 스택 및 직무 카테고리 추출...")
    skills, category = extract_skills_and_category(summary)
    print(f"  추출된 기술 스택: {skills}")
    print(f"  추정 직무 카테고리: {category}")

    # generate_query_from_report가 list를 반환할 경우 대비
    query_raw = generate_query_from_report(summary)

    if isinstance(query_raw, list):
        query = ' '.join(str(q) for q in query_raw).strip()
    else:
        query = str(query_raw).strip()

    print(f"  검색 쿼리 생성: '{query}'")

    # 5. FAISS 채용공고 추천
    print("\n[5] FAISS 채용공고 추천 시작...")

    # FAISS 검색 API 호출 → similarity_score 포함된 리스트 반환
    job_id_results = search_faiss_job_ids(query)  # → List[Dict] 형태: [{"job_id": ..., "similarity_score": ...}, ...]

    # job_id만 추출
    job_ids = [job["job_id"] for job in job_id_results]

    # RDB에서 상세 정보 조회
    recommendations = get_job_details_from_ids(job_ids)
    print(f"  추천된 채용공고 수: {len(recommendations)}")

    # 추천 내용 출력
    print("\n추천 결과 요약")
    if job_id_results and recommendations:
        for i, job in enumerate(recommendations, 1):
            matched = next((j for j in job_id_results if j["job_id"] == job["job_id"]), {})
            score = matched.get("similarity_score", 0.0)
            print(f"{i}. {job['position_title']} (유사도: {score:.3f})")
            print(f"   게시일: {job.get('posted_at', 'N/A')}")
            print(f"   설명 요약: {job.get('description', '')[:200]}...")
            print("-" * 60)
    else:
        print("추천 결과가 없습니다.")
        if not job_id_results:
            print("  → FAISS에서 유사한 채용공고를 찾지 못했습니다.")
        elif job_id_results and not recommendations:
            print("  → FAISS는 job_id를 반환했지만 DB에서 해당 공고를 찾지 못했습니다.")


    # CoT 추천 이유 상세 분석
    if recommendations:
        print("\n" + "="*80)
        print("추천 이유 상세 분석 (GPT Chain of Thought)")
        print("="*80)
        
        for i, job in enumerate(recommendations, 1):
            matched = next((j for j in job_id_results if j["job_id"] == job["job_id"]), {})
            score = matched.get("similarity_score", 0.0)
            
            print(f"\n[추천 #{i}] {job['position_title']}")
            print("-" * 50)
            
            # GPT CoT 분석 생성
            cot_analysis = generate_cot_analysis(
                user_skills=skills,
                user_category=category,
                job_description=job.get('description', ''),
                job_title=job['position_title'],
                similarity_score=score,
                search_query=query
            )
            
            print(cot_analysis)
            
            if i < len(recommendations):  # 마지막이 아니면 구분선
                print("\n" + "="*80)

    # 6. 결과 DB 저장
    print("\n[6] DB에 결과 저장 중...")
    resume_id = insert_to_database(user_id, blob_url, summary, skills, category, recommendations)
    print(f"  저장 완료. Resume ID: {resume_id}")

    print("\n전체 파이프라인 완료")
    return resume_id


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("user_id", type=int, help="사용자 ID")
    parser.add_argument("pdf_path", type=str, help="PDF 경로")
    args = parser.parse_args()

    run_pipeline(args.user_id, args.pdf_path)