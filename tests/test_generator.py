import copy
import json

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage

from travel_ai.generator import ItineraryGenerationError, build_context, build_messages, generate_itinerary
from travel_ai.schemas import ItineraryRequest

REQUEST = ItineraryRequest.model_validate({
    "city": "도쿄",
    "start_date": "2026-11-03",
    "end_date": "2026-11-03",
    "participants": [
        {"id": "me", "name": "진수", "quiz_selections": {"1": [1], "3": [2], "8": [1]}},
        {"id": "friend", "name": "민지", "quiz_selections": {"2": [0], "3": [2], "7": [0]}},
    ],
    "conditions": {"companion": "친구", "transport": "대중교통", "budget": "50만원-100만원", "tempo": "여유"},
})


def place(pid, concept, name="아무 이름", lat=0.0, lng=0.0):
    return {"id": pid, "name": name, "lat": lat, "lng": lng, "concept": concept}


GOOD = {
    "destination": "일본",
    "city": "도쿄",
    "days": [{
        "day": 1, "date": "2026-11-03", "title": "아사쿠사·우에노",
        "schedule": [
            {"time": "10:00", "end_time": "11:30", "title": "센소지", "mode": "alternate",
             "place": place("sensoji", "유적지"), "picked_by": ["me"], "description": "d", "reason": "r"},
            {"time": "12:00", "end_time": "13:30", "title": "도쿄 국립박물관", "mode": "alternate",
             "place": place("tokyo-national-museum", "전시"), "picked_by": ["friend"], "description": "d", "reason": "r"},
            {"time": "14:00", "end_time": "16:00", "title": "각자", "mode": "separate", "separate": [
                {"participant_ids": ["me"], "title": "스파", "place": place("spa-laqua", "온천·스파"), "description": "d", "reason": "r"},
                {"participant_ids": ["friend"], "title": "쇼핑", "place": place("ameyoko", "쇼핑 유형"), "description": "d", "reason": "r"},
            ]},
        ],
    }],
}


def fake(*replies):
    return FakeListChatModel(responses=[r if isinstance(r, str) else json.dumps(r, ensure_ascii=False) for r in replies])


def test_context_contains_comparison_and_places():
    ctx = build_context(REQUEST)

    assert ctx["dates"] == ["2026-11-03"]
    assert {c["name"] for c in ctx["comparison"]["common"]} == {"카페 투어"}
    assert any(p["id"] == "sensoji" for p in ctx["places"])
    assert "lat" not in ctx["places"][0]  # 좌표는 LLM 에 주지 않는다


def test_prompt_reflects_conditions():
    system = build_messages(REQUEST)[0].content
    assert "약 3개" in system  # 템포 '여유'
    assert "최대 1개" in system


def test_generate_hydrates_places_from_catalog():
    result = generate_itinerary(REQUEST, fake(GOOD))
    sensoji = result.days[0].schedule[0].place

    assert (sensoji.name, sensoji.lat, sensoji.lng) == ("센소지", 35.7148, 139.7967)


def test_concept_is_fixed_to_one_the_people_picked():
    reply = copy.deepcopy(GOOD)
    reply["days"][0]["schedule"][1]["place"]["concept"] = "유적지"  # 박물관은 유적지이기도 하지만 민지는 '전시'를 골랐다
    museum = generate_itinerary(REQUEST, fake(reply)).days[0].schedule[1].place

    assert museum.concept == "전시"


def test_strips_code_fence():
    reply = "```json\n" + json.dumps(GOOD, ensure_ascii=False) + "\n```"
    assert generate_itinerary(REQUEST, fake(reply)).city == "도쿄"


def test_accepts_content_block_list():
    # Gemini 3.x 는 content 를 [{"type": "text", "text": ...}] 블록 리스트로 돌려준다
    class BlockLLM:
        def invoke(self, messages):
            return AIMessage(content=[{"type": "text", "text": json.dumps(GOOD, ensure_ascii=False)}])

    assert generate_itinerary(REQUEST, BlockLLM()).city == "도쿄"


def test_retries_with_error_feedback_then_succeeds():
    bad = copy.deepcopy(GOOD)
    bad["days"][0]["schedule"][0]["place"]["id"] = "made-up-place"
    llm = fake(bad, GOOD)

    result = generate_itinerary(REQUEST, llm)

    assert result.days[0].schedule[0].place.id == "sensoji"


@pytest.mark.parametrize("mutate, message", [
    (lambda d: d["days"][0]["schedule"][0]["place"].update(id="made-up"), "후보 목록에 없는"),
    (lambda d: d["days"][0].update(date="2026-11-04"), "date"),
    (lambda d: d["days"][0]["schedule"][2]["separate"][0].update(participant_ids=["friend"]), "정확히 한 번씩"),
    (lambda d: d["days"][0]["schedule"].append(copy.deepcopy(d["days"][0]["schedule"][2]) | {"time": "17:00", "end_time": "18:00"}), "separate 항목이 2개"),
    (lambda d: d["days"][0]["schedule"][1].update(time="09:00"), "오름차순"),
    (lambda d: d["days"][0]["schedule"][0].update(picked_by=["ghost"]), "picked_by"),
    # 공통 컨셉(카페 투어)이 아닌 장소를 common 으로
    (lambda d: d["days"][0]["schedule"][0].update(mode="common", picked_by=None), "모두가 고른 컨셉"),
    # 센소지(유적지·대표 명소)는 민지 취향이 아니다
    (lambda d: d["days"][0]["schedule"][0].update(picked_by=["friend"]), "민지"),
    # 분리 그룹에 맞지 않는 장소
    (lambda d: d["days"][0]["schedule"][2]["separate"][0].update(participant_ids=["friend"]) or
               d["days"][0]["schedule"][2]["separate"][1].update(participant_ids=["me"]), "취향이 아니다"),
])
def test_rule_violations_fail_after_retries(mutate, message):
    bad = copy.deepcopy(GOOD)
    mutate(bad)
    with pytest.raises(ItineraryGenerationError, match=message):
        generate_itinerary(REQUEST, fake(bad, bad), max_attempts=2)


def test_invalid_json_fails():
    with pytest.raises(ItineraryGenerationError):
        generate_itinerary(REQUEST, fake("not json"), max_attempts=1)
