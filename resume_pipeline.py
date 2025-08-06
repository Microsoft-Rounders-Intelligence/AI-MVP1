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

# 환경 변수 로드
load_dotenv()

# Azure OpenAI 클라이언트 설정
client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version="2024-02-15-preview",
    azure_endpoint=os.getenv("OPENAI_ENDPOINT")
)

def generate_cot_analysis(user_skills, user_category, job_description, job_title, similarity_score, search_query):
    prompt = f"""당신은 채용공고 추천 시스템의 분석가입니다. 다음 정보를 바탕으로 왜 이 채용공고가 추천되었는지 논리적으로 분석해주세요.

**사용자 정보:**
- 직무 카테고리: {user_category}
- 기술 스택: {', '.join(user_skills) if user_skills else '정보 없음'}
- 검색 쿼리: {search_query}

**추천된 채용공고:**
- 직무명: {job_title}
- 유사도 점수: {similarity_score:.3f}
- 채용공고 내용: {job_description[:1000]}...

**분석 요청사항:**
1. 유사도 점수가 {similarity_score:.3f}인 이유를 분석해주세요
2. 사용자의 기술 스택과 채용공고의 요구사항이 어떻게 매칭되는지 설명해주세요
3. 직무 카테고리의 연관성을 분석해주세요
4. 최종적으로 이 추천이 적절한지 판단하고 그 근거를 제시해주세요

**출력 형식:**
간결하고 명확하게 단계별로 분석해주세요. 불필요한 수사나 과장은 피하고 객관적 사실에 기반해 설명해주세요."""
    
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

    query_raw = generate_query_from_report(summary)
    query = ' '.join(query_raw) if isinstance(query_raw, list) else str(query_raw).strip()
    print(f"  검색 쿼리 생성: '{query}'")

    # 5. FAISS 채용공고 추천
    print("\n[5] FAISS 채용공고 추천 시작...")
    job_id_results = search_faiss_job_ids(query)
    job_ids = [job["job_id"] for job in job_id_results]
    recommendations = get_job_details_from_ids(job_ids)

    # 🔥 score 병합
    for job in recommendations:
        matched = next((j for j in job_id_results if j["job_id"] == job["job_id"]), {})
        job["similarity_score"] = matched.get("similarity_score", 0.0)
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

    # 6. CoT 분석 결과 수집
    cot_analyses = []
    if recommendations:
        print("\n" + "="*80)
        print("추천 이유 상세 분석 (GPT Chain of Thought)")
        print("="*80)

        for i, job in enumerate(recommendations, 1):
            matched = next((j for j in job_id_results if j["job_id"] == job["job_id"]), {})
            score = matched.get("similarity_score", 0.0)

            print(f"\n[추천 #{i}] {job['position_title']}")
            print("-" * 50)

            cot_analysis = generate_cot_analysis(
                user_skills=skills,
                user_category=category,
                job_description=job.get('description', ''),
                job_title=job['position_title'],
                similarity_score=score,
                search_query=query
            )
            print(cot_analysis)
            cot_analyses.append(cot_analysis)

            if i < len(recommendations):
                print("\n" + "="*80)

    # 7. DB 저장
    print("\n[6] DB에 결과 저장 중...")
    resume_id = insert_to_database(
        user_id=user_id,
        blob_url=blob_url,
        summary=summary,
        skills=skills,
        category=category,
        job_recommendations=recommendations,
        search_query=query,
        cot_analyses=cot_analyses  # ✅ CoT 분석 결과 추가
    )
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
