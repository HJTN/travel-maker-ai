# 🧳 Travel Maker, "취향이 달라도 함께 떠나는 여행"

> 동행자 모두의 취향을 모아 공통·분리·번갈아 일정으로 조율하는 Travel Maker의 AI 일정 생성 파트입니다!

## 🎥 배포·시연 영상 링크

| 구분 | URL |
| :---: | :--- |
| **프론트엔드** | - |
| **백엔드** | - |
| **AI** | - |

---

## ✨ AI 핵심 기능 (Key Feature)

### 1. 사용자 취향 벡터화 & 저장

* **기능 소개**

> 사진 퀴즈 결과(음식, 여행, 문화생활, 여가 활동 등 카테고리별 선호)를 벡터로 바꿔 VectorDB에 저장합니다.<br/>
> 새로운 경험이나 피드백이 생기면 취향 벡터를 업데이트해 프로필을 최신 상태로 유지합니다.

* **처리 흐름**

> 사진 퀴즈 완료 (S03) → 취향 키워드·유형 분류 → 임베딩 → VectorDB (pgvector / Pinecone) 저장 → 취향 분석 결과 (S04)

### 2. 동행자 취향 비교 & 갈등 영역 분석

* **기능 소개**

> 여행 참여자들의 취향 벡터를 비교해 취향 일치도와 공통 관심사를 계산합니다.<br/>
> 선호도 차이가 큰 항목을 찾아 의견 충돌이 생길 수 있는 영역을 미리 파악합니다.

* **처리 흐름**

> 동행자 전원 퀴즈 완료 (S08) → 참여자 취향 벡터 조회 → 공통 취향 / 차이가 큰 취향 분류

### 3. LangChain 기반 여행 일정 생성

* **기능 소개**

> 공통 취향은 **함께하는 일정**, 서로 다른 취향은 **따로 보내는 시간** 또는 **번갈아 고르는 일정**으로 조율합니다.<br/>
> 인기순이 아니라 동행자 모두의 예상 만족도를 기준으로 장소(음식점, 카페, 여행지, 놀거리)를 고르고, 추천 이유를 함께 설명합니다.

* **처리 흐름**

> 여행지·기간 + 취향 비교 결과 → LangChain 플로우 (장소 탐색 → 일정 배치 → 추천 이유 생성) → Gemini API → 일정 확인 (S10)

---

## 🖼️ 전체 서비스 UI

> {Travel Maker 메인 페이지 화면(1875x1044)}

---

## ⚙️ 시스템 아키텍처 (AI 파트)

> {시스템 아키텍처 AI 부분 이미지(1875x1044)}

## ⛏️ 기술 스택

| 구분 | 기술 스택 |
| :---: | :--- |
| **프레임워크** | LangChain |
| **프로그래밍 언어** | Python |
| **LLM** | Google AI Studio (Gemini API) |
| **VectorDB** | pgvector, Pinecone |
| 기타 | Oracle Cloud Infrastructure (BE 팀과 공동 사용) |

---

## 🏗️ 아키텍처 구조

> AI 파트 전용 저장소입니다. 프론트엔드·백엔드는 각각 별도 저장소에서 관리합니다.

```text
travel-maker-ai/
├─ travel_ai/
│  ├─ quiz.py         # 사진 퀴즈 응답 → 취향 프로필
│  ├─ taxonomy.py     # 취향 컨셉 분류 (대분류·중분류·소분류)
│  ├─ compare.py      # 동행자 취향 비교, 공통 취향·갈등 영역 분석
│  ├─ places.py       # 도시별 장소 후보 (data/)
│  ├─ generator.py    # LangChain 일정 생성 플로우 (공통·분리·번갈아, 추천 이유)
│  ├─ schemas.py      # API 입출력 형식
│  └─ api.py          # FastAPI 서버 (BE 연동용)
├─ tests/             # pytest (가짜 LLM 사용)
├─ examples/          # API 요청 예시
├─ requirements.txt
└─ README.md
```

---

## 🚀 로컬 실행 방법

### 1. 가상환경 생성

> Python 가상환경을 만들고 활성화합니다.

```shell
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. 의존성 설치

> 필요한 패키지를 설치합니다.

```shell
pip install -r requirements.txt
```

### 3. 환경 변수 설정

> Google AI Studio에서 발급한 Gemini API 키와 VectorDB 접속 정보를 `.env`에 넣습니다. `.env`는 커밋하지 않습니다.

```shell
# .env (저장소 루트)
GOOGLE_API_KEY=발급받은_키
GEMINI_MODEL=gemini-3.6-flash   # 선택. 기본값 gemini-3.6-flash
```

### 4. 테스트 · 서버 실행

> 테스트는 가짜 LLM을 써서 API 키 없이 돌아갑니다. 서버는 실제 Gemini를 호출합니다.

```shell
python -X utf8 -m pytest -q
uvicorn travel_ai.api:app --reload      # http://localhost:8000/docs 에서 요청·응답 형식 확인
```

---

## 🔌 API (BE 연동용)

| 메서드 | 경로 | 설명 |
| :---: | :--- | :--- |
| `GET` | `/health` | 상태 확인 |
| `POST` | `/itineraries` | 동행자 전원의 퀴즈 응답 + S05 조건 → 일정 (S10). 요청 예시: `examples/tokyo_request.json` |

`/itineraries` 응답 (실제 Gemini 기준 1회 30~60초):

| 상태 | `code` | `retryable` | 의미 → 화면 |
| :---: | :--- | :---: | :--- |
| 200 | - | - | 일정 생성 성공 → S10 |
| 400 | `UNSUPPORTED_CITY` | false | 장소 데이터가 없는 도시 (현재 도쿄만) |
| 422 | - | false | 요청 형식 오류 (FastAPI 기본 형식) |
| 502 | `GENERATION_FAILED` | true | AI가 3번 시도해도 규칙에 맞는 일정을 못 만듦 → S09 재시도 |
| 503 | `LLM_UNAVAILABLE` | true | Gemini 과부하·한도 초과·타임아웃 → S09 재시도 |
| 500 | `LLM_ERROR` | false | API 키 등 설정 문제 |

---

## 📋 파이프라인 구성

| 호출 시점 | 처리 단계 | 주요 기능 |
| :--- | :---: | :--- |
| `S03 사진 퀴즈 완료` | 취향 벡터화 | 퀴즈 결과를 벡터로 바꿔 VectorDB에 저장 |
| `S08 동행자 전원 퀴즈 완료` | AI 일정 생성 | 취향 비교 → 공통·분리·번갈아 일정 생성 |
| `S09 재시도` / `S10 재생성` | AI 일정 재생성 | 생성에 실패했거나 사용자가 다시 요청하면 일정을 다시 생성 |
