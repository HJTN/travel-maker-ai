# 기술 스택 & 역할 분담

## 저장소

| 직렬 | 저장소 |
|---|---|
| AI | 이 저장소 (`travel-maker-ai`) |
| FE | 별도 저장소 (`gdg-frontend/`). 원래 AI 파트도 이 저장소의 `gdg-AI/`에 있었다 |
| BE | 별도 저장소 |

## 기술 스택 (기획 기준)

| 직렬 | 스택 |
|---|---|
| FE | React, JavaScript, Vite, Tailwind CSS |
| BE | Web Framework (Spring Boot / Node.js 중 결정), DB (미정), Google Cloud Platform (Cloud Run) |
| AI | Python, LangChain, Google AI Studio (Gemini API), (MVP 이후) VectorDB (pgvector, Pinecone) |
| DE | Figma, Adobe Illustrator |
| 협업 | GitHub (Projects, Wiki, Repository), Notion, KakaoTalk |

## 역할 분담

| 이름 | 직렬 | 담당 |
|---|---|---|
| 김경민 | FE | 접속, 로그인, 사진 퀴즈, 여행 조사, 친구 초대, 일정 생성, 일정 확인 (S01~S10) |
| 배병윤 | FE | 메인 화면: 지도, 일정 탭, 일정 목록 (S11~S15) |
| 김지원 | BE | 사용자 인증 및 로그인 API |
| 전정민 | BE | 사용자 취향 데이터 관리, 사진 퀴즈 API |
| 정희균 | BE | 여행 일정 관리 API, AI 일정 생성 파이프라인 연동 |
| 허진수 | AI | LLM 모델 결정, LangChain 일정 생성 플로우, (MVP 이후) pgvector/Pinecone 구축, 취향 벡터화 (BE와 협업) |
| 김지환 | DE | 비주얼 디자인, 로고 디자인 |
| 전병진 | DE | 비주얼 디자인, 로고 디자인 |
