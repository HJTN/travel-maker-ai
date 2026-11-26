# BE 피드백 반영 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** BE 직렬 피드백 6개를 반영해, BE의 Job 워커가 그대로 부를 수 있는 Stateless AI 일정 생성 서버를 GCP Cloud Run에 올린다.

**Architecture:** API 입출력 JSON 키를 BE와 같은 `snake_case`로 바꾸고, 퀴즈 입력을 인덱스 대신 BE의 문항·선택지 키(`question_key`, `selected_option_keys`)로 받는다. 일정 생성은 `async`(LLM `ainvoke`)로 바꿔 긴 호출에도 서버가 막히지 않게 하고, 저장은 전부 BE가 맡는다. 마지막에 Docker 이미지로 Cloud Run(서울 리전)에 비공개 서비스로 배포한다.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, LangChain + Gemini(`langchain-google-genai`), pytest, Docker, Google Cloud Run · Secret Manager

**Spec:** 이 문서의 "배경" 섹션. BE 피드백 원문 6개와 BE 위키 [API-Spec](https://github.com/jungminmobile/travelMakerBE/wiki/API-Spec)의 "퀴즈 문항 및 선택지 기준표 (quiz_version v1.0)", "AI 일정 생성 Job" 절이 근거다.

## 배경 (BE 피드백 → 결정)

| # | BE 피드백 | 결정 | 담당 Task |
|---|---|---|---|
| 1 | 호출 타임아웃 → 비동기로 | **A안**: BE Job 워커가 AI 서버를 긴 타임아웃(권장 180초)으로 호출해 응답을 기다린다. AI 서버는 `async` 엔드포인트 + `ainvoke` | Task 4 |
| 2 | 저장은 BE, AI는 Stateless | 이미 Stateless. 문서로 명시 | Task 5 |
| 3 | S04 화면 없음 | AI에 S04 API를 만들지 않는다. `build_profile`은 일정 생성 내부용으로만 둔다 | Task 5 |
| 4 | GCP에 BE·AI 함께 배포 | Cloud Run `asia-northeast3`, 비공개 + BE 서비스 계정에 `run.invoker` | Task 6 |
| 5 | MVP에서 취향 벡터화 제외 | 코드엔 없음. 문서에서 VectorDB를 "MVP 이후"로 옮긴다 | Task 5 |
| 6 | `quizSelections` → 키값 | BE 위키 키 그대로 사용 (`answers` + `quiz_version`) | Task 2 |
| - | JSON 키 형식 | AI API를 BE와 같은 `snake_case`로 통일 | Task 1 |
| - | BE Job 요청의 `special_requests` | 받아서 프롬프트에 넣는다. `include_budget_optimization`은 MVP에서 받지 않음 | Task 3 |

**⚠️ Task 1 시작 전에 BE에 확인받을 것 (Task 0).** 답이 위 결정과 다르면 해당 Task만 고친다.

## Global Constraints

- 작업 브랜치: `feature/be-feedback` (main 직접 커밋 금지). 저장소 루트: `travel-maker-ai/`
- 테스트 명령: `.venv/Scripts/python -X utf8 -m pytest -q` — 각 Task 커밋 전 전체 통과
- 테스트는 API 키·네트워크 없이 돈다. LLM은 `FakeListChatModel` 또는 `ainvoke`를 가진 가짜 객체로 바꾼다
- 주석·docstring·에러 메시지·프롬프트는 한국어, 식별자는 영어 (`.claude/docs/conventions.md`)
- 잘못된 입력은 한국어 메시지 `ValueError` → FastAPI 422. 새 오류 코드는 만들지 않는다
- 커밋: `<type>: <한국어 요약>`, 파일을 명시해 `git add`. **`Co-Authored-By`·`Generated with Claude Code` 등 AI 저자 문구 금지** (`.claude/skills/git-commit`)
- `.env`(`GOOGLE_API_KEY`)는 절대 커밋하지 않는다

## Review Focus

1. **FE/BE 라벨이 어긋난 퀴즈 키**(예: 옛 `SCENIC_VIEW` 대신 다른 키) → 500이 아니라 422 + 어떤 키가 틀렸는지 한국어 메시지. → Task 2 `test_unknown_quiz_key_is_422`
2. **컨셉이 하나도 없는 참여자**(숙소 문항만 답했거나 전부 `[]`) → 컨텍스트 생성이 죽지 않는다. → Task 2 `test_context_with_participant_without_concepts`
3. **예전 camelCase로 보낸 요청** → 조용히 기본값으로 처리되지 않고 422. → Task 1 `test_request_rejects_camel_case`
4. **async 전환 뒤 Gemini 오류** → 지금처럼 503/500 매핑 유지. → Task 4 (기존 `test_failures_map_to_s09_errors`를 `ainvoke` 가짜로)
5. **`special_requests`에 규칙을 무시하라는 문장** → 시스템 프롬프트가 아니라 사용자 메시지에만 들어가고, 후보 밖 장소는 기존 규칙 검사에서 걸린다. → Task 3 `test_special_requests_only_in_human_message`

---

### Task 0: 준비 & BE 확인 (오전 첫 작업, 코드 없음)

**Files:**
- Modify: `docs/pull-request-template.md` (이미 수정된 상태, 커밋만)

- [ ] **Step 1: main 최신화 후 작업 브랜치 생성** (수정 중인 템플릿은 그대로 따라온다)

```bash
git switch main && git pull origin main
git switch -c feature/be-feedback
git status --short   # M docs/pull-request-template.md 만 보여야 함
```

- [ ] **Step 2: 템플릿 커밋**

```bash
git add docs/pull-request-template.md
git commit -m "docs: PR 템플릿을 travel_ai 모듈 구조와 create-pr 스킬 기준으로 갱신"
```

- [ ] **Step 3: BE에 아래 4가지를 보내고 답을 이 문서 "배경" 표에 반영**
  1. 호출 방식 A안(긴 타임아웃 동기 호출, 권장 180초) 괜찮은지
  2. 퀴즈 키는 위키 기준표를 그대로 쓴다. 단 위키 라벨이 현재 프론트 화면과 5곳 다름(Q2 풍경명소, Q3 풍경열차탐방, Q6 캡슐호텔, Q9 명상·요가·테마파크) → 최종 라벨이 위키 쪽인지
  3. AI API JSON 키를 `snake_case`로 맞추는 것
  4. `special_requests`를 AI 요청에 그대로 넘겨 줄 수 있는지, 출력의 `reason`은 BE가 `recommendation_reason`으로 매핑하는지

- [ ] **Step 4: 기준선 테스트**

Run: `.venv/Scripts/python -X utf8 -m pytest -q`
Expected: `49 passed`

---

### Task 1: API JSON 키를 snake_case로 통일

**Files:**
- Modify: `travel_ai/schemas.py` (`_Model`, 모듈 docstring, `_check` 에러 메시지)
- Modify: `travel_ai/generator.py` (`SYSTEM_PROMPT`의 `pickedBy` → `picked_by`, `durationMin`은 장소 데이터 키라 그대로)
- Modify: `tests/test_schemas.py`, `tests/test_generator.py`(`REQUEST`, `GOOD`), `tests/test_api.py`, `examples/tokyo_request.json`

**Interfaces:**
- Produces: 모든 요청·응답 JSON 키가 Python 필드명과 같다 (`start_date`, `end_date`, `quiz_selections`, `end_time`, `picked_by`, `participant_ids`, `max_separate_blocks_per_day`). `model_dump(by_alias=True)` 호출은 남겨 둬도 결과가 같다.

- [ ] **Step 1: 실패하는 테스트 작성/수정** (`tests/test_schemas.py`)

```python
def test_request_rejects_camel_case():
    camel = {**REQUEST, "startDate": REQUEST["start_date"], "endDate": REQUEST["end_date"]}
    del camel["start_date"], camel["end_date"]
    with pytest.raises(ValidationError):
        ItineraryRequest.model_validate(camel)


def test_response_round_trips_as_snake_case():
    resp = ItineraryResponse.model_validate(RESPONSE)
    assert resp.model_dump(mode="json", exclude_none=True) == RESPONSE
```

`REQUEST`, `RESPONSE`, `GOOD`, `BODY`, 예시 JSON의 키를 전부 snake_case로 바꾼다. `test_request_parses_camel_case_and_defaults` → `test_request_parses_snake_case_and_defaults`, `test_creates_itinerary_in_camel_case` → `..._in_snake_case`이고 단언은 `first["picked_by"] == ["me"] and first["end_time"] == "11:30"`.

- [ ] **Step 2: 실패 확인**

Run: `.venv/Scripts/python -X utf8 -m pytest -q`
Expected: FAIL (`startDate`가 alias라 snake_case 키를 못 읽음)

- [ ] **Step 3: `schemas._Model`에서 `alias_generator=to_camel`을 빼고 `to_camel` import 삭제.** 모듈 docstring의 "camelCase 로 주고받는다"를 "BE API 와 같은 snake_case"로, `_check` 메시지의 `endDate`→`end_date`, `pickedBy`→`picked_by`로 고친다. `SYSTEM_PROMPT`의 `pickedBy`도 `picked_by`로.

- [ ] **Step 4: 통과 확인**

Run: `.venv/Scripts/python -X utf8 -m pytest -q`
Expected: 전부 PASS

- [ ] **Step 5: 커밋**

```bash
git add travel_ai/schemas.py travel_ai/generator.py tests/test_schemas.py tests/test_generator.py tests/test_api.py examples/tokyo_request.json
git commit -m "feat: AI API JSON 키를 BE와 같은 snake_case로 통일"
```

---

### Task 2: 퀴즈 입력을 BE 문항·선택지 키로 변경 (피드백 6)

**Files:**
- Modify: `travel_ai/quiz.py` (`QUIZ`, `LODGING_QUESTION`, `build_profile`)
- Modify: `travel_ai/schemas.py` (`QuizAnswer` 추가, `Participant`)
- Modify: `travel_ai/generator.py` (`build_context`, `_hydrate_and_check`의 `build_profile(p.quiz_selections)` 2곳)
- Modify: `tests/test_quiz.py`, `tests/test_compare.py`, `tests/test_schemas.py`, `tests/test_generator.py`, `tests/test_api.py`, `examples/tokyo_request.json`

**Interfaces:**
- Consumes: Task 1의 snake_case 필드
- Produces:
  - `quiz.QUIZ: dict[str, dict[str, tuple[str, str | None]]]` — `{question_key: {option_key: (한글 라벨, 소분류 또는 None)}}`, 문항 순서 = 아래 표 순서
  - `quiz.LODGING_QUESTION = "Q_ACCOMMODATION"`
  - `quiz.build_profile(selections: dict[str, list[str]]) -> dict` — 반환 형식은 지금과 같음(`categories`, `concepts`, `lodging`). 모르는 문항·선택지 키는 `ValueError("알 수 없는 퀴즈 키: Q_X / OPT")`. 같은 선택지가 두 번 오면 한 번만 센다
  - `schemas.QuizAnswer(question_key: str, selected_option_keys: list[str])`
  - `schemas.Participant(id, name, quiz_version: Literal["v1.0"] = "v1.0", answers: list[QuizAnswer])` + 메서드 `selections() -> dict[str, list[str]]`. `answers` 안의 `question_key` 중복과 `QUIZ`에 없는 키는 validator에서 `ValueError`

**키 표** (BE 위키 v1.0. 인덱스는 옛 `quizSelections` 번호 — 테스트 픽스처 번역용):

| 문항(옛 idx) | question_key | 선택지 0 / 1 / 2 / 3 → 소분류 |
|---|---|---|
| 0 | `Q_DESTINATION` | `MOUNTAIN` 산→트레킹·등산 / `CAMPING` 캠핑→캠핑 / `SEA` 바다→해변 / `CITY` 도심→로컬 산책 |
| 1 | `Q_PLACE` | `LANDMARK` 랜드마크→대표 명소 / `HISTORIC_SITE` 유적지→유적지 / `SCENIC_VIEW` 풍경명소→계절 경관 / `ISLAND` 섬→섬 |
| 2 | `Q_TIME` | `EXHIBITION` 전시관람→전시 / `TREKKING` 트레킹·등산→트레킹·등산 / `SCENIC_TRAIN` 풍경열차탐방→계절 경관 / `NIGHT_VIEW` 야경→대표 명소 |
| 3 | `Q_FOOD` | `LOCAL_FOOD` 로컬음식→로컬 음식 / `FINE_DINING` 파인다이닝→파인다이닝 / `CAFE_TOUR` 카페 투어→카페 투어 / `MARKET_FOOD` 시장먹거리→시장 먹거리 |
| 4 | `Q_EVENING` | `LOCAL_PUB` 전통주점→술 여행 / `WINE_BAR` 와인바→술 여행 / `LOCAL_RESTAURANT` 로컬식당→로컬 음식 / `NIGHT_MARKET` 야시장→시장 먹거리 |
| 5 | `Q_ACCOMMODATION` | `CAMPGROUND` 캠핑장 / `HOTEL_RESORT` 호텔·리조트 / `GUESTHOUSE` 게스트하우스 / `CAPSULE_HOTEL` 캡슐호텔 (모두 None, lodging) |
| 6 | `Q_EXPERIENCE` | `LOCAL_FESTIVAL` 지역 축제→지역 축제 / `CRAFT_MAKING` 공예만들기→만들기 / `EXTREME_SPORTS` 익스트림스포츠→익스트림 / `RURAL_EXPERIENCE` 농촌체험→농촌·생활 |
| 7 | `Q_FREE_TIME` | `SHOPPING` 쇼핑→쇼핑 유형 / `PERFORMANCE` 공연 관람→공연 관람 / `WATER_PLAY` 물놀이→물놀이 / `ALLEY_WALK` 골목 산책→로컬 산책 |
| 8 | `Q_RELAXATION` | `MEDITATION_YOGA` 명상·요가→명상·리트릿 / `HOT_SPRING_SPA` 온천·스파→온천·스파 / `ANIMAL_INTERACTION` 동물 교감→놀이시설 / `THEME_PARK` 테마파크→놀이시설 |

> `SCENIC_TRAIN`은 예전 "촬영지 탐방"이 바뀐 것이라 소분류를 **계절 경관(자연 경관)**으로 새로 정했다. Task 0 답에 따라 바뀔 수 있다.

- [ ] **Step 1: 실패하는 테스트 작성** (`tests/test_quiz.py`)

```python
def test_quiz_keys_match_be_spec():
    assert list(QUIZ) == ["Q_DESTINATION", "Q_PLACE", "Q_TIME", "Q_FOOD", "Q_EVENING",
                          "Q_ACCOMMODATION", "Q_EXPERIENCE", "Q_FREE_TIME", "Q_RELAXATION"]
    assert all(len(options) == 4 for options in QUIZ.values())
    assert all(c is None or c in CONCEPTS for options in QUIZ.values() for _, c in options.values())


def test_build_profile_counts_and_ratios():
    profile = build_profile({"Q_DESTINATION": ["MOUNTAIN"], "Q_TIME": ["TREKKING", "NIGHT_VIEW"],
                             "Q_FOOD": ["CAFE_TOUR"], "Q_ACCOMMODATION": ["HOTEL_RESORT"]})

    assert profile["concepts"][0] == {"name": "트레킹·등산", "category": "관광", "group": "자연 경관", "count": 2}
    assert profile["categories"] == {"관광": 0.75, "미식": 0.25, "휴식": 0.0, "체험": 0.0}
    assert profile["lodging"] == ["호텔·리조트"]


def test_build_profile_ignores_duplicate_option():
    assert build_profile({"Q_FOOD": ["CAFE_TOUR", "CAFE_TOUR"]})["concepts"][0]["count"] == 1


def test_build_profile_rejects_unknown_key():
    with pytest.raises(ValueError, match="Q_DESTINATION / VOLCANO"):
        build_profile({"Q_DESTINATION": ["VOLCANO"]})
```

`test_build_profile_rejects_unknown_option`(IndexError)는 지운다. `test_taxonomy_matches_xlsx`, `test_build_profile_empty`(`{}`)는 유지.

`tests/test_schemas.py`:

```python
def test_participant_answers_to_selections():
    p = Participant.model_validate({"id": "me", "name": "나", "answers": [
        {"question_key": "Q_FOOD", "selected_option_keys": ["CAFE_TOUR"]},
        {"question_key": "Q_TIME", "selected_option_keys": []}]})
    assert p.quiz_version == "v1.0"
    assert p.selections() == {"Q_FOOD": ["CAFE_TOUR"], "Q_TIME": []}


def test_participant_rejects_duplicate_question_key():
    answer = {"question_key": "Q_FOOD", "selected_option_keys": ["CAFE_TOUR"]}
    with pytest.raises(ValidationError):
        Participant.model_validate({"id": "me", "name": "나", "answers": [answer, answer]})
```

`tests/test_api.py` (Review Focus 1):

```python
def test_unknown_quiz_key_is_422(client):
    use(fake(GOOD))
    bad = copy.deepcopy(BODY)
    bad["participants"][0]["answers"][0]["selected_option_keys"] = ["SCENIC_PHOTO"]
    res = client.post("/itineraries", json=bad)

    assert res.status_code == 422
    assert "SCENIC_PHOTO" in res.text
```

`tests/test_generator.py` (Review Focus 2):

```python
def test_context_with_participant_without_concepts():
    req = REQUEST.model_copy(update={"participants": [
        REQUEST.participants[0],
        Participant(id="x", name="숙소만", answers=[QuizAnswer(question_key="Q_ACCOMMODATION", selected_option_keys=["GUESTHOUSE"])]),
    ]})
    ctx = build_context(req)

    assert ctx["participants"][1]["concepts"] == [] and ctx["participants"][1]["lodging"] == ["게스트하우스"]
```

모든 픽스처(`test_compare.py`의 `build_profile({"0": [0], ...})`, `REQUEST`, 예시 JSON)는 위 키 표로 번역한다. 예: `{"1": [1], "3": [2], "8": [1]}` → `answers: [Q_PLACE/HISTORIC_SITE, Q_FOOD/CAFE_TOUR, Q_RELAXATION/HOT_SPRING_SPA]`. `test_compare.py`는 `build_profile({"Q_DESTINATION": ["MOUNTAIN"], ...})` 형태로 바로 넘긴다.

- [ ] **Step 2: 실패 확인**

Run: `.venv/Scripts/python -X utf8 -m pytest -q`
Expected: FAIL (`QUIZ`가 list, `Participant`에 `answers` 없음)

- [ ] **Step 3: 구현.** `QUIZ`를 표대로 dict로 다시 쓰고 `build_profile`은 `dict.fromkeys`로 선택지 중복을 없앤 뒤 `QUIZ[question_key][option_key]`를 찾는다(없으면 위 메시지로 `ValueError`). `Participant`의 `model_validator(mode="after")`에서 중복 문항과 미지 키를 검사한다(`build_profile(self.selections())`를 한 번 호출해 같은 메시지를 쓰면 된다). `generator.py`의 두 곳을 `build_profile(p.selections())`로 바꾼다. `quiz.py` 모듈 docstring의 "gdg-frontend/src/App.jsx 의 quizQuestions" 근거를 "BE 위키 API-Spec 퀴즈 기준표 v1.0"으로 바꾼다.

- [ ] **Step 4: 통과 확인**

Run: `.venv/Scripts/python -X utf8 -m pytest -q`
Expected: 전부 PASS

- [ ] **Step 5: 커밋**

```bash
git add travel_ai/quiz.py travel_ai/schemas.py travel_ai/generator.py tests/ examples/tokyo_request.json
git commit -m "feat: 퀴즈 입력을 BE 문항·선택지 키(answers) 기반으로 변경 (S03)"
```

---

### Task 3: `special_requests` 받아서 프롬프트에 반영

**Files:**
- Modify: `travel_ai/schemas.py` (`ItineraryRequest`), `travel_ai/generator.py` (`build_context`)
- Test: `tests/test_schemas.py`, `tests/test_generator.py`

**Interfaces:**
- Produces: `ItineraryRequest.special_requests: str | None = Field(default=None, max_length=1000)`. `build_context`가 값이 있을 때만 `"special_requests"` 키를 넣는다 → `HumanMessage`에만 들어간다

- [ ] **Step 1: 실패하는 테스트**

```python
# tests/test_schemas.py
def test_special_requests_max_1000():
    with pytest.raises(ValidationError):
        ItineraryRequest.model_validate({**REQUEST, "special_requests": "가" * 1001})

# tests/test_generator.py  (Review Focus 5)
def test_special_requests_only_in_human_message():
    req = REQUEST.model_copy(update={"special_requests": "둘째 날 오전은 쉬고 싶어요"})
    system, human = build_messages(req)

    assert "둘째 날 오전은 쉬고 싶어요" in human.content
    assert "둘째 날 오전은 쉬고 싶어요" not in system.content
```

- [ ] **Step 2: 실패 확인** — Run: `.venv/Scripts/python -X utf8 -m pytest -q` / Expected: 위 2개 FAIL
- [ ] **Step 3: 필드 추가 + `build_context`에 조건부 키 추가.** `SYSTEM_PROMPT`의 "지켜야 할 것"에 한 줄 추가: `- special_requests 가 있으면 위 규칙을 지키는 범위에서 반영한다.`
- [ ] **Step 4: 통과 확인** — 전체 PASS
- [ ] **Step 5: 커밋**

```bash
git add travel_ai/schemas.py travel_ai/generator.py tests/test_schemas.py tests/test_generator.py
git commit -m "feat: BE Job 요청의 special_requests를 일정 생성 프롬프트에 반영"
```

---

### Task 4: 일정 생성을 async로 전환 + 생성 시간 측정 (피드백 1)

**Files:**
- Modify: `travel_ai/generator.py` (`generate_itinerary`, `__main__`), `travel_ai/api.py` (`create_itinerary`)
- Test: `tests/test_generator.py`, `tests/test_api.py`

**Interfaces:**
- Produces: `async def generate_itinerary(request: ItineraryRequest, llm, max_attempts: int = 3) -> ItineraryResponse` — `await llm.ainvoke(messages)` 사용. `api.create_itinerary`는 `async def`

- [ ] **Step 1: 테스트를 async 호출로 수정.** 새 의존성 없이 `asyncio.run(generate_itinerary(REQUEST, fake(GOOD)))`로 부른다. `test_api.py`의 `Raising`에 `async def ainvoke(self, messages): raise self.error`를 추가하고 `invoke`는 지운다(동기 경로가 남아 있으면 이 테스트가 깨지도록).
- [ ] **Step 2: 실패 확인** — Run: `.venv/Scripts/python -X utf8 -m pytest -q` / Expected: `coroutine` 관련 FAIL
- [ ] **Step 3: 구현.** `generate_itinerary`를 `async def` + `(await llm.ainvoke(messages)).text`로, `api.create_itinerary`를 `async def` + `await generate_itinerary(...)`로 바꾸고 "스레드풀에서 돌린다" 주석을 지운다. `__main__`은 `asyncio.run(...)`. docstring을 `llm: LangChain 채팅 모델 (ainvoke(messages) -> AIMessage).`로.
- [ ] **Step 4: 통과 확인** — 전체 PASS (Review Focus 4: `test_failures_map_to_s09_errors` 3건 포함)
- [ ] **Step 5: 실제 Gemini로 생성 시간 3회 측정** (`.env` 필요, 네트워크 사용)

```bash
for i in 1 2 3; do /usr/bin/time -f "%e s" .venv/Scripts/python -X utf8 -m travel_ai.generator examples/tokyo_request.json > /dev/null; done
```

Expected: 3회 모두 일정 JSON 출력 성공. 최댓값을 기록해 Task 5 README에 "1회 N~M초, BE 타임아웃 권장 = 최댓값 × 2 이상(최소 180초)"으로 적는다. (`/usr/bin/time`이 없으면 PowerShell `Measure-Command`)

- [ ] **Step 6: 커밋**

```bash
git add travel_ai/generator.py travel_ai/api.py tests/test_generator.py tests/test_api.py
git commit -m "feat: 일정 생성 API를 async로 전환 (BE Job 워커 장시간 호출 대응)"
```

---

### Task 5: 문서 정리 (피드백 2·3·5 + Task 1~4 반영)

**Files:**
- Modify: `README.md`, `.claude/docs/features.md`, `.claude/docs/team.md`, `.claude/docs/conventions.md`, `CLAUDE.md`, `travel_ai/quiz.py`(docstring 1줄), `travel_ai/api.py`(docstring 실행 경로 `gdg-AI 폴더에서` → `저장소 루트에서`)

- [ ] **Step 1: README 수정**
  - 기능 1 "사용자 취향 벡터화 & 저장"(17~26행) → "퀴즈 응답 → 취향 프로필 (일정 생성 내부용, 규칙 기반)"으로 바꾸고, 벡터화·VectorDB는 "MVP 이후" 한 줄로
  - 기능 2의 "취향 벡터 비교" 표현 → "취향 프로필 비교"
  - 기술 스택 표의 VectorDB 행 삭제, "Oracle Cloud Infrastructure" → "Google Cloud Platform (Cloud Run, BE와 공동 사용)"
  - `.env` 설명에서 "VectorDB 접속 정보" 삭제
  - API 절: 요청 예시를 snake_case + `answers` 형식으로, "AI 서버는 아무것도 저장하지 않는다(Stateless). 저장은 BE가 맡는다", Task 4 측정 시간과 권장 타임아웃, `special_requests`(선택, 1000자) 추가
  - 파이프라인 표의 "S03 사진 퀴즈 완료 / 취향 벡터화" 행 삭제
- [ ] **Step 2: `.claude/docs` 수정** — `features.md` 43행 VectorDB 저장을 "MVP 이후"로, `team.md` 17행 AI 스택에서 VectorDB를 "(MVP 이후)"로·BE 인프라를 GCP로, `conventions.md`의 "JSON 키는 camelCase" → "BE API와 같은 snake_case (alias 없음)", `by_alias=True` 규칙 삭제
- [ ] **Step 3: `quiz.py` 모듈 docstring 첫 줄** `S03 사진 퀴즈 응답 -> S04 취향 프로필.` → `S03 사진 퀴즈 응답 -> 일정 생성용 취향 프로필 (S04 화면용 API 아님).`
- [ ] **Step 4: 남은 흔적 확인**

Run: `grep -rn -i "vectordb\|camelCase\|quizSelections\|Oracle" README.md CLAUDE.md .claude/docs travel_ai examples`
Expected: "MVP 이후" 문맥 외 결과 없음

- [ ] **Step 5: 전체 테스트** — Expected: PASS
- [ ] **Step 6: 커밋**

```bash
git add README.md CLAUDE.md .claude/docs/features.md .claude/docs/team.md .claude/docs/conventions.md travel_ai/quiz.py travel_ai/api.py
git commit -m "docs: BE 피드백 반영 (Stateless·S04 제외·벡터화 MVP 제외·snake_case·GCP)"
```

---

### Task 6: Docker 이미지 + Cloud Run 배포 (피드백 4)

**Files:**
- Create: `Dockerfile`, `.dockerignore`
- Modify: `README.md` (배포 절 추가)

**Interfaces:**
- Produces: Cloud Run 서비스 `travel-maker-ai` (`asia-northeast3`, 비공개, 요청 타임아웃 300초). BE 서비스 계정만 `roles/run.invoker`. BE는 ID 토큰(audience = 서비스 URL)을 붙여 호출한다

- [ ] **Step 1: `Dockerfile` 작성** — `python:3.14-slim`, `requirements.txt` 먼저 복사해 설치 후 `travel_ai/`만 복사, `CMD ["sh", "-c", "uvicorn travel_ai.api:app --host 0.0.0.0 --port ${PORT:-8080}"]`. `.dockerignore`: `.venv/ .env .git/ tests/ docs/ .claude/ __pycache__/ .pytest_cache/`
- [ ] **Step 2: 로컬 빌드·실행 확인**

```bash
docker build -t travel-maker-ai .
docker run --rm -d -p 8080:8080 --env-file .env --name tm-ai travel-maker-ai
curl -s localhost:8080/health   # Expected: {"status":"ok"}
docker stop tm-ai
```

- [ ] **Step 3: GCP 준비 (소유자 계정, 1회)**

```bash
gcloud config set project <PROJECT_ID>
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com
printf '%s' "<GOOGLE_API_KEY>" | gcloud secrets create gemini-api-key --data-file=-
```

- [ ] **Step 4: 배포**

```bash
gcloud run deploy travel-maker-ai --source . --region asia-northeast3 \
  --no-allow-unauthenticated --timeout 300 --memory 512Mi \
  --set-secrets GOOGLE_API_KEY=gemini-api-key:latest
```

Expected: `Service URL: https://travel-maker-ai-....run.app`. 빌드 권한 오류가 나면 메시지에 나온 서비스 계정에 `roles/run.builder`, 실행 계정에 `roles/secretmanager.secretAccessor`를 준다.

- [ ] **Step 5: 동작 확인**

```bash
curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" <SERVICE_URL>/health
# Expected: {"status":"ok"}  (토큰 없이 호출하면 403)
```

- [ ] **Step 6: BE 호출 권한** — BE 서비스 계정 이메일을 받아:

```bash
gcloud run services add-iam-policy-binding travel-maker-ai --region asia-northeast3 \
  --member="serviceAccount:<BE_SA_EMAIL>" --role="roles/run.invoker"
```

- [ ] **Step 7: README "배포" 절 추가** (Step 3~6 명령, 서비스 URL은 적지 않고 BE에 따로 전달) **후 커밋**

```bash
git add Dockerfile .dockerignore README.md
git commit -m "chore: Cloud Run 배포용 Dockerfile과 배포 가이드 추가"
```

---

### Task 7: PR 생성

- [ ] **Step 1: `.claude/skills/create-pr` 스킬대로 PR 작성.** 제목 `feat: BE 피드백 반영 (snake_case·퀴즈 키·async·Cloud Run)`. "리뷰 포인트"에 반드시: 퀴즈 라벨 5곳 차이와 `SCENIC_TRAIN→계절 경관` 결정, 요청 형식 변경(`answers`, snake_case, `special_requests`), 권장 타임아웃 값, `reason` ↔ `recommendation_reason` 매핑, ID 토큰 호출 방식.
- [ ] **Step 2:** 제목·본문을 사용자에게 보여주고 승인 후 `git push -u origin HEAD` → `gh pr create --base main`
