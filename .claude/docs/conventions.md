# 코딩 컨벤션 (AI 파트, Python)

> 현재 `travel_ai/`, `tests/` 코드에서 쓰는 방식을 정리했다. 새 코드는 이 규칙과 주변 코드를 따른다.
> 규칙과 기존 코드가 어긋나면 임의로 고치지 말고 먼저 알린다.

## 언어·문서화
- 주석, docstring, 에러 메시지, 프롬프트는 **한국어**로 쓴다. 식별자는 영어로 쓴다.
- 모든 모듈은 첫 줄에 docstring을 둔다. 모듈이 하는 일과 흐름을 쓰고, 관련 화면이 있으면 화면 ID(S01~S17)를 쓴다.
  - 예: `"""동행자 취향 비교 (S08 이후, 일정 생성 전 단계)."""`
- 주석은 "무엇"보다 "왜"를 쓴다. 코드만 보고 알 수 없는 제약·근거(프론트 관례, 화면 시안, LLM 특성 등)를 남긴다.
- 함수 docstring은 인자 형식이나 예외 조건처럼 시그니처로 드러나지 않는 것만 짧게 쓴다.
  - 예: `"""profiles: {참여자 id: build_profile 결과}. 참여자는 2명 이상."""`

## 이름·구조
- 함수·변수·모듈: `snake_case` / 클래스: `PascalCase` / 상수: `UPPER_SNAKE_CASE` (모듈 상단).
- 모듈 내부용 함수·클래스는 `_` 접두사를 붙이고, 공개 함수 **아래에** 둔다.
- 모듈은 기능 단위로 나눈다 (`quiz`, `compare`, `places`, `generator`, `api`, `schemas`, `taxonomy`). 한 파일이 커지기 전에는 미리 쪼개지 않는다.
- 데이터 파일은 `travel_ai/data/`에 두고 `Path(__file__).parent` 기준으로 찾는다.

## import
- 순서: 표준 라이브러리 → 서드파티 → 패키지 내부. 묶음 사이에 빈 줄 하나.
- 패키지 내부는 상대 import(`from .schemas import ...`)를 쓴다.
- `datetime`은 `import datetime as dt`로 쓴다 (필드명 `date`와 충돌 방지).
- 무겁거나 API 키가 필요한 모듈(`langchain_google_genai` 등)은 쓰는 함수 안에서 import해 테스트가 키 없이 돌게 한다.

## 타입·데이터
- 공개 함수에는 타입 힌트를 단다. 내장 제네릭(`list[str]`, `dict[str, int]`)을 쓴다 (`typing.List` 쓰지 않음).
- **입출력 경계(API 요청·응답, LLM 출력)는 Pydantic v2 모델**로 정의한다 (`schemas.py`).
  - `_Model`을 상속해 JSON 키와 Python 속성 모두 BE API와 같은 snake_case로 쓴다 (alias 없음).
  - 선택지가 정해진 값은 `Literal`로 정의하고, 문자열은 프론트 화면 라벨과 같게 맞춘다.
- 모듈 내부 중간 결과(취향 프로필, 비교 결과 등)는 일반 `dict`/`list`로 둔다. 필요해지기 전에 클래스로 만들지 않는다.
- 파일을 읽고 쓸 때는 항상 `encoding="utf-8"`, JSON 덤프는 `ensure_ascii=False`.

## 에러 처리
- 잘못된 입력·규칙 위반은 한국어 메시지와 함께 `ValueError`를 던진다.
- 화면 분기와 연결되는 실패는 전용 예외 클래스로 만들고 docstring에 화면을 적는다 (예: `ItineraryGenerationError` → S09).
- API 오류 응답은 `ErrorResponse`(`code`, `message`, `retryable`) 형식을 따른다. 새 오류 코드를 추가하면 README의 응답 표도 같이 고친다.
- 처리할 수 없는 예외를 넓게 잡아 삼키지 않는다.

## LLM
- LLM 객체는 함수 인자로 주입받는다 (`await generate_itinerary(request, llm)`, API에서는 `Depends(get_llm)`). 테스트에서 가짜 LLM으로 바꿀 수 있게 하기 위해서다.
- 모델 이름은 `GEMINI_MODEL` 환경변수로 받고, 비밀 값은 `.env`에만 둔다.
- LLM 출력은 그대로 믿지 않는다. Pydantic 검증 + 규칙 검사 후, 문제를 LLM에 돌려주며 재시도한다.
- 장소 등 사실 데이터는 LLM이 지어내지 않게 후보 id로만 고르게 하고, 실제 값은 데이터에서 덮어쓴다.

## 테스트
- pytest, `tests/test_<모듈>.py`에 `test_<동작>` 형태의 평범한 함수로 쓴다. 클래스로 묶지 않는다.
- 테스트는 API 키·네트워크 없이 돌아야 한다. LLM은 가짜 객체(`ainvoke(messages)`를 가진 클래스)로 대체한다.
- 준비 → 빈 줄 → `assert` 순서로 쓰고, 기대값은 가능하면 전체 값을 비교한다.
- 실행: `python -X utf8 -m pytest -q`. 코드를 바꾸면 커밋 전에 전체 테스트를 돌린다.

## 형식
- 들여쓰기 4칸, 문자열은 큰따옴표.
- 포매터·린터는 아직 정하지 않았다. 도입하려면 먼저 확인받는다. 관련 없는 줄의 형식만 바꾸는 수정은 하지 않는다.

## Git
- 커밋·PR 규칙은 `.claude/skills/git-commit`, `.claude/skills/create-pr` 스킬을 따른다.
