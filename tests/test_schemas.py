import pytest
from pydantic import ValidationError

from travel_ai.schemas import ItineraryRequest, ItineraryResponse, ScheduleItem

REQUEST = {
    "city": "도쿄",
    "startDate": "2026-11-03",
    "endDate": "2026-11-05",
    "participants": [
        {"id": "me", "name": "나", "quizSelections": {"0": [0], "3": [2]}},
        {"id": "friend", "name": "동행자 1", "quizSelections": {"3": [2], "7": [0]}},
    ],
    "conditions": {"companion": "친구", "transport": "대중교통", "budget": "50만원-100만원", "tempo": "적당히"},
}

SENSOJI = {"id": "sensoji", "name": "센소지", "lat": 35.7148, "lng": 139.7967, "concept": "유적지"}
KAPPABASHI = {"id": "kappabashi", "name": "갓파바시", "lat": 35.7127, "lng": 139.7880, "concept": "쇼핑 유형"}
SUMIDA = {"id": "sumida-park", "name": "스미다 공원", "lat": 35.7126, "lng": 139.8023, "concept": "계절 경관"}

# mockItinerary.js 의 Day 1 을 새 형식으로 옮긴 것
RESPONSE = {
    "destination": "일본",
    "city": "도쿄",
    "days": [
        {
            "day": 1,
            "date": "2026-11-03",
            "title": "도쿄 대표 명소 여행",
            "schedule": [
                {
                    "time": "10:00", "endTime": "11:30", "title": "센소지 방문", "mode": "alternate",
                    "place": SENSOJI, "pickedBy": ["me"],
                    "description": "도쿄에서 가장 오래된 사찰", "reason": "나의 유적지 취향, 동행자도 관광 선호",
                },
                {
                    "time": "14:00", "endTime": "16:00", "title": "각자 즐기는 오후", "mode": "separate",
                    "separate": [
                        {"participantIds": ["friend"], "title": "갓파바시", "place": KAPPABASHI,
                         "description": "조리도구와 식기점", "reason": "동행자의 쇼핑 취향"},
                        {"participantIds": ["me"], "title": "스미다 공원", "place": SUMIDA,
                         "description": "스미다강 산책", "reason": "나의 자연 경관 취향"},
                    ],
                },
            ],
        }
    ],
}


def test_request_parses_camel_case_and_defaults():
    req = ItineraryRequest.model_validate(REQUEST)

    assert req.destination == "일본"
    assert req.participants[0].quiz_selections == {0: [0], 3: [2]}
    assert req.options.max_separate_blocks_per_day == 1


def test_request_rejects_unknown_condition_value():
    bad = {**REQUEST, "conditions": {**REQUEST["conditions"], "tempo": "아주 바쁨"}}
    with pytest.raises(ValidationError):
        ItineraryRequest.model_validate(bad)


def test_request_rejects_reversed_dates_and_duplicate_ids():
    with pytest.raises(ValidationError):
        ItineraryRequest.model_validate({**REQUEST, "endDate": "2026-11-01"})
    with pytest.raises(ValidationError):
        ItineraryRequest.model_validate({**REQUEST, "participants": [REQUEST["participants"][0]] * 2})


def test_response_round_trips_as_camel_case():
    resp = ItineraryResponse.model_validate(RESPONSE)
    dumped = resp.model_dump(mode="json", by_alias=True, exclude_none=True)

    assert dumped == RESPONSE


def test_schedule_item_mode_rules():
    base = {"time": "10:00", "endTime": "11:00", "title": "x"}
    with pytest.raises(ValidationError, match="place"):
        ScheduleItem.model_validate({**base, "mode": "common"})
    with pytest.raises(ValidationError, match="pickedBy"):
        ScheduleItem.model_validate({**base, "mode": "alternate", "place": SENSOJI})
    with pytest.raises(ValidationError, match="2개 이상"):
        ScheduleItem.model_validate({**base, "mode": "separate", "separate": []})
    with pytest.raises(ValidationError):
        ScheduleItem.model_validate({**base, "time": "9:00", "mode": "common", "place": SENSOJI})
