# AI-MVP1: 이력서 분석 기반 채용공고 추천

AI 기반 텍스트 처리와 벡터 유사도 검색을 활용한 자동화된 이력서 분석 및 맞춤형 채용공고 추천 시스템입니다.

## 개요

PDF 이력서를 분석하고 개인화된 채용공고를 추천하는 엔드투엔드 파이프라인을 제공합니다. Azure OpenAI를 활용한 지능형 텍스트 분석, FAISS 기반 벡터 유사도 검색, 그리고 추천 결정에 대한 상세한 Chain of Thought 설명을 제공합니다.

## 핵심 기능

- **PDF 텍스트 추출**: PyMuPDF를 활용한 정확한 텍스트 파싱
- **AI 기반 이력서 분석**: Azure OpenAI GPT-4를 통한 지능형 평가
- **기술 스택 및 카테고리 추출**: 기술 스킬과 직무 카테고리 자동 추출
- **벡터 기반 채용공고 검색**: FAISS 기반 유사도 검색을 통한 관련 채용공고 발견
- **Chain of Thought 분석**: 추천 근거에 대한 GPT 생성 설명
- **클라우드 스토리지 연동**: Azure Blob Storage를 통한 안전한 파일 저장
- **데이터 영속성**: 분석 결과 및 추천 이력을 위한 MySQL 연동

## 시스템 아키텍처

```
PDF 이력서 → 텍스트 추출 → GPT 분석 → 기술/카테고리 추출 → FAISS 검색 → 추천 결과 → CoT 분석 → 데이터베이스 저장
     ↓            ↓           ↓               ↓               ↓           ↓           ↓            ↓
Azure Blob    PyMuPDF   Azure OpenAI    정규식 파싱      Vector DB     MySQL      GPT-4     MySQL
```

## 기술 스택

### 핵심 기술
- **Python 3.8+**
- **Azure OpenAI GPT-4**: 이력서 분석 및 추론 생성
- **FAISS**: 고성능 벡터 유사도 검색
- **MySQL**: 관계형 데이터 영속성
- **Azure Blob Storage**: 클라우드 파일 저장

### 주요 의존성
- `PyMuPDF (fitz)`: PDF 텍스트 추출
- `openai`: Azure OpenAI API 클라이언트
- `pymysql`: MySQL 데이터베이스 연결
- `requests`: HTTP API 통신
- `python-dotenv`: 환경 설정 관리

## 설치 및 설정

### 1. 저장소 설정
```bash
git clone https://github.com/Microsoft-Rounders-Intelligence/AI-MVP1.git
cd AI-MVP1
```

### 2. 환경 구성
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate     # Windows
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정
`.env` 파일을 생성하고 다음과 같이 구성하세요:

```env
# Azure Blob Storage
AZURE_BLOB_CONN_STRING=your-blob-connection-string
AZURE_BLOB_CONTAINER=your-container-name

# Azure OpenAI 설정
OPENAI_API_KEY=your-openai-api-key
OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
OPENAI_DEPLOYMENT=gpt-4

# MySQL 데이터베이스
EMBED_DB_HOST=your-mysql-host
EMBED_DB_PORT=3306
EMBED_DB_USER=your-mysql-user
EMBED_DB_PASSWORD=your-mysql-password
USER_DATABASE_NAME=your-user-database
EMBEDDING_DATABASE_NAME=your-job-database

# FAISS 검색 서비스
FAISS_SEARCH_URL=http://localhost:5000/search
FAISS_API_PORT=5000

# OpenAI 임베딩 설정
EMBED_OPENAI_API_KEY=your-embedding-api-key
EMBED_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
EMBED_OPENAI_DEPLOYMENT=text-embedding-3-large
EMBED_OPENAI_API_VERSION=2023-05-15
```

## 사용법

### 기본 실행
```bash
python resume_pipeline.py [user_id] [pdf_path]
```

### 실행 예시
```bash
python resume_pipeline.py 1 "/path/to/resume.pdf"
```

### 예상 출력
```
이력서 자동 분석 파이프라인 시작

[1] Azure Blob 업로드 시작...
  업로드 완료. Blob URL: https://...

[2] 이력서에서 텍스트 추출 중...
  텍스트 추출 완료

[3] GPT 기반 이력서 평가 중...
  평가 완료

[4] 기술 스택 및 직무 카테고리 추출...
  추출된 기술 스택: ['Python', 'Django', 'MySQL']
  추정 직무 카테고리: 백엔드 개발자

[5] FAISS 채용공고 추천 시작...
  추천된 채용공고 수: 5

추천 결과 요약
1. Python 백엔드 개발자 (유사도: 0.845)
   게시일: 2024-08-01
   설명 요약: Python과 Django를 활용한 백엔드 개발...

================================================================================
추천 이유 상세 분석 (GPT Chain of Thought)
================================================================================

[추천 #1] Python 백엔드 개발자
--------------------------------------------------
[GPT가 생성한 상세 분석 내용]

[6] DB에 결과 저장 중...
  저장 완료. Resume ID: 123

전체 파이프라인 완료
```

## 프로젝트 구조

```
AI-MVP1/
├── resume_pipeline.py              # 메인 파이프라인 오케스트레이터
├── resume_analysis.py              # 이력서 분석 모듈
├── upload_to_blob.py              # Azure Blob Storage 연동
├── recommend_jobs_from_faiss.py   # FAISS 검색 모듈
├── store_to_db.py                 # 데이터베이스 영속성 레이어
├── requirements.txt               # 패키지 의존성
├── .env.example                   # 환경 변수 템플릿
└── README.md                      # 프로젝트 문서
```

## 주요 모듈

### `resume_pipeline.py`
결과 Chain-of-thought  으로 출력 및
전체 분석 파이프라인을 조율하는 메인 오케스트레이션 모듈입니다.

### `resume_analysis.py`
핵심 분석 기능들:
- `extract_text_from_pdf()`: PDF 텍스트 추출
- `evaluate_resume()`: GPT 기반 이력서 평가
- `extract_skills_and_category()`: 기술 스택 및 카테고리 추출
- `generate_query_from_report()`: 검색 쿼리 생성

### `recommend_jobs_from_faiss.py`
벡터 검색 및 채용공고 조회:
- `search_faiss_job_ids()`: FAISS 벡터 유사도 검색
- `get_job_details_from_ids()`: 채용공고 상세 정보 조회

### `store_to_db.py`
데이터베이스 연산:
- `insert_to_database()`: MySQL로 분석 결과 저장

## 기능

### Chain of Thought 분석
각 추천에 대한 상세한 추론을 제공하기 위해 GPT-4를 활용합니다:
- 유사도 점수 해석
- 기술 스킬 매칭 분석
- 직무 카테고리 연관성 평가
- 최종 추천 근거 제시

### 오류 처리
- FAISS 응답 형식 검증
- 누락된 데이터 필드 처리
- API 실패 시 graceful degradation
- 데이터베이스 연결 오류 복구

## FAISS 검색 API 연동

별도의 FAISS 검색 서버가 필요하며, 다음과 같은 응답 형식을 기대합니다:

```python
{
    "results": [
        {"job_id": 123, "similarity_score": 0.845},
        {"job_id": 456, "similarity_score": 0.782}
    ]
}
```

## 데이터 저장 스키마

### Resume 테이블
분석 결과가 `parsed_json` 필드에 JSON 형식으로 저장됩니다:
```json
{
    "summary": "GPT 분석 요약",
    "skills": ["Python", "Django"],
    "category": "백엔드 개발자",
    "analysis_timestamp": "2024-08-05T10:30:00"
}
```

### JobRecommendation 테이블
유사도 점수와 타임스탬프를 포함한 추천 메타데이터가 저장됩니다.


## 시스템 요구사항

- Python 3.8 이상
- MySQL 5.7+ 또는 8.0+
- OpenAI 및 Blob Storage 서비스가 포함된 Azure 구독
- FAISS 검색 서비스 (별도 배포)
- 처리를 위한 최소 4GB RAM
- API 호출을 위한 네트워크 연결

