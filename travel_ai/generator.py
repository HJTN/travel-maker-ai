"""LangChain + Gemini 일정 생성.

흐름: 요청 -> 취향 프로필·비교 -> 프롬프트 -> LLM(JSON) -> 형식·규칙 검증 -> (실패 시 오류를 돌려주며 재시도)
LLM 은 장소를 후보 id 로만 고르고, 이름·좌표는 후보 데이터로 덮어쓴다.
"""

import asyncio
import datetime as dt
import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import ValidationError

from .compare import compare_profiles
from .places import load_places
from .quiz import build_profile
from .schemas import ItineraryRequest, ItineraryResponse

# 여행 템포 -> 하루 일정 개수
ITEMS_PER_DAY = {"여유": 3, "조금 여유": 4, "적당히": 5, "조금 바쁨": 6, "바쁨": 7}

SYSTEM_PROMPT = """너는 동행자들의 서로 다른 취향을 조율해 일본 여행 일정을 만드는 플래너다.
한 사람에게 치우치지 않고, 인기순이 아니라 동행자 모두의 예상 만족도를 기준으로 고른다.

일정 항목의 mode 규칙:
- common: 공통 컨셉(comparison.common, 모든 참여자가 고른 컨셉)의 장소에만 쓴다. 공통 컨셉이 없거나 다 썼으면 common 대신 alternate 를 쓴다.
- alternate: 한 사람의 취향 장소에 다 같이 가며, picked_by 에 그 컨셉을 고른 참여자 id 를 넣는다. 차이 컨셉 중 mode 가 alternate 인 것을 먼저 쓰고, separate 한도를 넘는 separate 컨셉도 alternate 로 쓸 수 있다. 하루 안에서 서로의 취향이 번갈아, 사람별로 고르게 나오게 한다.
- separate: 차이 컨셉 중 mode 가 separate 인 것. 같은 시간대에 그룹별로 다른 장소에 간다. separate 배열에 그룹을 2개 이상 넣고, 모든 참여자가 정확히 한 그룹에 속해야 한다.

지켜야 할 것:
- 장소는 반드시 후보 목록의 id 로만 고른다. 목록에 없는 장소를 만들지 않는다.
- 장소는 그곳에 가는 사람의 취향이어야 한다: common 은 전원, alternate 는 picked_by 전원, separate 는 그룹원 전원이 고른 컨셉(participants[].concepts)을 그 장소의 concepts 에 가지고 있어야 한다. place.concept 은 그 컨셉이다.
- 하루 separate 항목은 최대 {max_separate}개.
- 하루 일정은 약 {items_per_day}개, 시간은 "HH:MM" 24시간제, 겹치지 않게 오름차순.
- 이동 수단({transport})을 고려해 하루 일정은 가까운 권역(area)끼리 묶는다. 근교 장소는 하루를 통째로 쓸 때만 넣는다.
- 예산({budget})에 맞게 고른다.
- reason 에는 누구의 어떤 취향 때문에 골랐는지 참여자 이름으로 한 문장 쓴다. description 은 장소 소개 한두 문장.
- 같은 장소를 여러 번 넣지 않는다.
- special_requests 가 있으면 위 규칙을 지키는 범위에서 반영한다.

아래 JSON Schema 를 따르는 JSON 객체 하나만 출력한다. 설명이나 코드블록 표시는 쓰지 않는다.
{schema}"""


class ItineraryGenerationError(Exception):
    """재시도 후에도 올바른 일정을 만들지 못했을 때 (S09 생성 실패 화면으로)."""


def build_context(request: ItineraryRequest) -> dict:
    profiles = {p.id: build_profile(p.selections()) for p in request.participants}
    context = {
        "destination": request.destination,
        "city": request.city,
        "dates": [str(request.start_date + dt.timedelta(days=i)) for i in range(_day_count(request))],
        "participants": [
            {"id": p.id, "name": p.name, "concepts": [c["name"] for c in profiles[p.id]["concepts"]], "lodging": profiles[p.id]["lodging"]}
            for p in request.participants
        ],
        "comparison": compare_profiles(profiles) if len(profiles) >= 2 else None,
        "places": [
            {k: place[k] for k in ("id", "name", "area", "concepts", "durationMin")} for place in load_places(request.city)
        ],
    }
    # 사용자 자유 입력이라 시스템 프롬프트가 아닌 HumanMessage 데이터로만 전달한다
    if request.special_requests:
        context["special_requests"] = request.special_requests
    return context


def build_messages(request: ItineraryRequest) -> list:
    system = SYSTEM_PROMPT.format(
        max_separate=request.options.max_separate_blocks_per_day,
        items_per_day=ITEMS_PER_DAY[request.conditions.tempo],
        transport=request.conditions.transport,
        budget=request.conditions.budget,
        schema=json.dumps(ItineraryResponse.model_json_schema(by_alias=True), ensure_ascii=False),
    )
    human = "여행 정보:\n" + json.dumps(build_context(request), ensure_ascii=False)
    return [SystemMessage(system), HumanMessage(human)]


async def generate_itinerary(request: ItineraryRequest, llm, max_attempts: int = 3) -> ItineraryResponse:
    """llm: LangChain 채팅 모델 (ainvoke(messages) -> AIMessage)."""
    messages = build_messages(request)
    error = None
    for _ in range(max_attempts):
        text = (await llm.ainvoke(messages)).text  # content 가 문자열이든 블록 리스트든 텍스트만
        try:
            itinerary = ItineraryResponse.model_validate_json(_strip_code_fence(text))
            _hydrate_and_check(itinerary, request)
            return itinerary
        except (ValidationError, ValueError) as e:
            error = e
            messages = messages + [AIMessage(text), HumanMessage(f"출력에 문제가 있다. 고쳐서 JSON 전체를 다시 출력해라.\n{e}")]
    raise ItineraryGenerationError(str(error))


def _hydrate_and_check(itinerary: ItineraryResponse, request: ItineraryRequest) -> None:
    """규칙 위반 시 ValueError. 통과하면 장소 이름·좌표를 후보 데이터로 덮어쓴다.

    장소는 그곳에 가는 사람(common 은 전원, alternate 는 picked_by, separate 는 그룹원)이
    모두 고른 컨셉이어야 하고, place.concept 은 그중 하나로 맞춘다.
    """
    catalog = {p["id"]: p for p in load_places(request.city)}
    participant_ids = {p.id for p in request.participants}
    name_of = {p.id: p.name for p in request.participants}
    liked = {p.id: {c["name"] for c in build_profile(p.selections())["concepts"]} for p in request.participants}
    expected_dates = [request.start_date + dt.timedelta(days=i) for i in range(_day_count(request))]
    problems = []

    if [d.date for d in itinerary.days] != expected_dates:
        problems.append(f"days 의 date 는 {[str(d) for d in expected_dates]} 순서여야 한다.")

    for day in itinerary.days:
        separate_count = sum(item.mode == "separate" for item in day.schedule)
        if separate_count > request.options.max_separate_blocks_per_day:
            problems.append(f"{day.day}일차 separate 항목이 {separate_count}개로 너무 많다.")
        times = [item.time for item in day.schedule]
        if times != sorted(times):
            problems.append(f"{day.day}일차 일정 시간이 오름차순이 아니다.")

        for item in day.schedule:
            # (장소, 그 장소에 가는 사람들, 그 장소를 고른 근거가 되는 사람들)
            if item.mode == "common":
                visits = [(item.place, participant_ids)]
            elif item.mode == "alternate":
                visits = [(item.place, item.picked_by)]
                if not set(item.picked_by) <= participant_ids:
                    problems.append(f"{item.title}: picked_by 에 없는 참여자 id 가 있다.")
                    visits = []
            else:
                visits = [(g.place, g.participant_ids) for g in item.separate]
                members = [pid for g in item.separate for pid in g.participant_ids]
                if sorted(members) != sorted(participant_ids):
                    problems.append(f"{item.title}: separate 그룹은 모든 참여자를 정확히 한 번씩 포함해야 한다.")
                    visits = []

            for place, who in visits:
                if place.id not in catalog:
                    problems.append(f"'{place.id}' 는 후보 목록에 없는 장소다.")
                    continue
                src = catalog[place.id]
                place.name, place.lat, place.lng = src["name"], src["lat"], src["lng"]
                matches = [c for c in src["concepts"] if all(c in liked[pid] for pid in who)]
                if matches:
                    if place.concept not in matches:
                        place.concept = matches[0]
                elif item.mode == "common":
                    problems.append(f"{item.title}: '{src['name']}' 는 모두가 고른 컨셉(공통 컨셉)의 장소가 아니다. 공통 컨셉이 없으면 alternate 로 바꿔라.")
                else:
                    names = ", ".join(name_of[pid] for pid in who)
                    problems.append(f"{item.title}: '{src['name']}' ({src['concepts']}) 는 {names} 의 취향이 아니다.")

    if problems:
        raise ValueError("\n".join(problems))


def _day_count(request: ItineraryRequest) -> int:
    return (request.end_date - request.start_date).days + 1


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return text


if __name__ == "__main__":
    # 실제 Gemini 호출: python -m travel_ai.generator examples/tokyo_request.json
    import os
    import sys
    from pathlib import Path

    from dotenv import load_dotenv
    from langchain_google_genai import ChatGoogleGenerativeAI

    load_dotenv()
    req = ItineraryRequest.model_validate_json(Path(sys.argv[1]).read_text(encoding="utf-8"))
    model = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
        temperature=0.7,
        response_mime_type="application/json",
        timeout=60,
        max_retries=2,
    )
    result = asyncio.run(generate_itinerary(req, model))
    print(result.model_dump_json(by_alias=True, exclude_none=True, indent=2))
