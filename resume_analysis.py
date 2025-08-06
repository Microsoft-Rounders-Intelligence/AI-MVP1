import os
import fitz  # PyMuPDF
import re
from openai import AzureOpenAI
from dotenv import load_dotenv
from typing import Tuple

load_dotenv()

# GPT 클라이언트 설정
client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    azure_endpoint=os.getenv("OPENAI_ENDPOINT"),
    api_version="2024-02-15-preview"
)

def extract_text_from_pdf(pdf_path: str) -> str:
    """PDF에서 텍스트 추출"""
    doc = fitz.open(pdf_path)
    return "\n".join([page.get_text() for page in doc])

def evaluate_resume(text: str) -> str:
    """GPT를 사용해 이력서 평가"""
    prompt = f"""
다음은 한 사람의 이력서입니다:

{text}

이 이력서를 분석하여 다음 정보를 한국어로 작성해 주세요. 각 항목에 대해 **왜 그렇게 판단했는지** 반드시 포함해 주세요.

1. 강점
2. 약점
3. 개선점
4. 예상 직무 카테고리
5. 기술 스택 목록
"""
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_DEPLOYMENT"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return response.choices[0].message.content

def extract_skills_and_category(report_text: str) -> Tuple[list, str]:
    """
    GPT 리포트에서 기술 스택과 직무 카테고리를 추출
    """
    skills_match = re.findall(r"(?:기술\s*스택|기술\s*목록)[^\n]*:\s*(.*)", report_text)
    category_match = re.findall(r"(?:직무\s*카테고리|직무\s*분류|직무\s*유형)[^\n]*:\s*(.*)", report_text)

    skills = [s.strip() for s in re.split(r"[,\•·]", skills_match[0])] if skills_match else []
    category = category_match[0].strip() if category_match else None
    return skills, category

# def generate_search_query(report: str) -> str:
#     """
#     GPT에게 직무 요약을 기반으로 간결한 검색 쿼리를 생성하게 함
#     """
#     prompt = f"""
# 다음 이력서 평가 내용을 바탕으로 FAISS 검색에 적합한 **간결한 키워드 기반 검색어**를 생성해 주세요.
# 불필요한 설명은 빼고, 핵심 직무 카테고리와 기술 키워드만 포함해 주세요. (20단어 이하)

# 이력서 평가 요약:
# {report}

# 검색어:
# """
#     response = client.chat.completions.create(
#         model=os.getenv("OPENAI_DEPLOYMENT"),
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.2
#     )
#     return response.choices[0].message.content.strip()

def generate_search_query(report: str) -> str:
    prompt = f"""
다음 이력서 평가 내용을 바탕으로 FAISS 검색에 적합한 **간결한 키워드 기반 검색어**를 생성해 주세요.

- 문장이 아닌 키워드만 나열해 주세요 (예: 데이터분석, Python, SQL)
- 핵심 직무와 기술 키워드 중심으로 구성해 주세요
- 결과는 쉼표(,)로 구분된 단어 10개 이하로 작성해 주세요
- 100자 이내로 제한해 주세요

이력서 평가 요약:
{report}

검색어:
"""
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_DEPLOYMENT"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return response.choices[0].message.content.strip()[:100]  # 100자 이내 제한


def generate_query_from_report(report_text: str) -> Tuple[str, list, str]:
    """
    GPT 리포트에서 기술/직무 추출 → GPT 검색어 생성까지 한 번에
    """
    skills, category = extract_skills_and_category(report_text)
    gpt_query = generate_search_query(report_text)
    return gpt_query, skills, category


def parse_resume_sections(report: str) -> Tuple[str, str, str]:
    """
    GPT 이력서 평가 리포트에서 강점, 약점, 개선점을 파싱한다.
    """
    # 구분자 기준으로 파싱
    strength_match = re.search(r"1\.\s*강점\s*[\:\-\n]?(.*?)\n\s*2\.", report, re.DOTALL)
    weakness_match = re.search(r"2\.\s*약점\s*[\:\-\n]?(.*?)\n\s*3\.", report, re.DOTALL)
    improvement_match = re.search(r"3\.\s*개선점\s*[\:\-\n]?(.*?)\n\s*4\.", report, re.DOTALL)

    strength = strength_match.group(1).strip() if strength_match else None
    weakness = weakness_match.group(1).strip() if weakness_match else None
    improvement = improvement_match.group(1).strip() if improvement_match else None

    return strength, weakness, improvement


# 테스트용 예시 실행
if __name__ == "__main__":
    pdf_path = "resume.pdf"
    text = extract_text_from_pdf(pdf_path)
    report = evaluate_resume(text)
    query, skills, category = generate_query_from_report(report)

    print("📄 평가 요약:\n", report)
    print("\n🔍 추천 쿼리:", query)
    print("🎯 기술 스택:", skills)
    print("📌 카테고리:", category)
