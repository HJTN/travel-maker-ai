# Travel Maker — AI 파트

동행자들의 취향을 분석하고, AI가 공통·분리·번갈아 일정으로 조율해 지도 위 하나의 여행길로 보여주는 서비스 (일본 여행 대상).

**이 저장소는 Travel Maker의 AI 직렬 전용 저장소다.**
- FE·BE 코드는 이 저장소에 없다. 다른 직렬과 맞춰야 하는 것(요청·응답 형식, 화면 라벨 등)은 코드를 고치지 말고 리뷰 포인트로 남겨 사용자에게 확인받는다.
- 코드·문서에 남아 있는 `gdg-frontend/...` 경로는 프론트엔드 저장소 안의 파일을 가리킨다.
- AI 서버는 BE가 서버 간 호출로 쓴다 (`README.md`의 API 표 참고).

## 저장소 구조
- `travel_ai/`: AI 일정 생성 패키지 (Python, LangChain, Gemini, FastAPI)
  - `quiz.py`(퀴즈 → 취향 프로필), `compare.py`(동행자 취향 비교), `places.py` + `data/`(도시별 장소 후보), `generator.py`(LLM 일정 생성), `schemas.py`(입출력 형식), `api.py`(HTTP API)
- `tests/`: pytest. 가짜 LLM을 써서 API 키 없이 돈다
- `examples/`: API 요청 예시
- `docs/core-documents/`: 기획안 원본(.pdf), 퀴즈 컨셉 분류(.xlsx, `tests/test_quiz.py`가 읽음)
- `docs/assets/`: 일정 화면 시안

## 명령 (저장소 루트에서)
- 테스트: `.venv/Scripts/python -X utf8 -m pytest -q`
- 서버: `.venv/Scripts/uvicorn travel_ai.api:app --reload` (`.env`에 `GOOGLE_API_KEY` 필요)

## 기획 (항상 참고)
@.claude/docs/overview.md
@.claude/docs/user-flow.md

## 코딩 컨벤션 (항상 따름)
@.claude/docs/conventions.md

## 참고 문서 (필요할 때 읽기)
- 기능 명세 (MVP / 부차 기능, AI 활용): `.claude/docs/features.md`
- 기술 스택 & 역할 분담: `.claude/docs/team.md`

## 작업 규칙
- 코드를 작성·수정·리뷰할 때는 항상 `andrej-karpathy-skills:karpathy-guidelines` 스킬을 먼저 불러와 따른다.
- 화면은 `user-flow.md`의 화면 ID(S01~S17)로 부른다.
- S16, S17(커뮤니티)은 후순위다. 요청이 없으면 구현하지 않는다.
