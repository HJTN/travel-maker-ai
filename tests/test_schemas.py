import pytest
from pydantic import ValidationError

from travel_ai.schemas import ItineraryRequest, ItineraryResponse, Participant, ScheduleItem

REQUEST = {
    "city": "도쿄",
    "start_date": "2026-11-03",
    "end_date": "2026-11-05",
    "participants": [
        {"id": "me", "name": "나", "answers": [{"question_key": "Q_DESTINATION", "selected_option_keys": ["MOUNTAIN"]}, {"question_key": "Q_FOOD", "selected_option_keys": ["CAFE_TOUR"]}]},
        {"id": "friend", "name": "동행자 1", "answers": [{"question_key": "Q_FOOD", "selected_option_keys": ["CAFE_TOUR"]}, {"question_key": "Q_FREE_TIME", "selected_option_keys": ["SHOPPING"]}]},
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
                    "time": "10:00", "end_time": "11:30", "title": "센소지 방문", "mode": "alternate",
                    "place": SENSOJI, "picked_by": ["me"],
                    "description": "도쿄에서 가장 오래된 사찰", "reason": "나의 유적지 취향, 동행자도 관광 선호",
                },
                {
                    "time": "14:00", "end_time": "16:00", "title": "각자 즐기는 오후", "mode": "separate",
                    "separate": [
                        {"participant_ids": ["friend"], "title": "갓파바시", "place": KAPPABASHI,
                         "description": "조리도구와 식기점", "reason": "동행자의 쇼핑 취향"},
                        {"participant_ids": ["me"], "title": "스미다 공원", "place": SUMIDA,
                         "description": "스미다강 산책", "reason": "나의 자연 경관 취향"},
                    ],
                },
            ],
        }
    ],
}


def test_request_parses_snake_case_and_defaults():
    req = ItineraryRequest.model_validate(REQUEST)

    assert req.destination == "일본"
    assert req.participants[0].selections() == {"Q_DESTINATION": ["MOUNTAIN"], "Q_FOOD": ["CAFE_TOUR"]}
    assert req.options.max_separate_blocks_per_day == 1


def test_request_rejects_camel_case():
    camel = {**REQUEST, "startDate": REQUEST["start_date"], "endDate": REQUEST["end_date"]}
    del camel["start_date"], camel["end_date"]
    with pytest.raises(ValidationError):
        ItineraryRequest.model_validate(camel)


def test_request_rejects_unknown_condition_value():
    bad = {**REQUEST, "conditions": {**REQUEST["conditions"], "tempo": "아주 바쁨"}}
    with pytest.raises(ValidationError):
        ItineraryRequest.model_validate(bad)


def test_request_rejects_reversed_dates_and_duplicate_ids():
    with pytest.raises(ValidationError):
        ItineraryRequest.model_validate({**REQUEST, "end_date": "2026-11-01"})
    with pytest.raises(ValidationError):
        ItineraryRequest.model_validate({**REQUEST, "participants": [REQUEST["participants"][0]] * 2})


def test_response_round_trips_as_snake_case():
    resp = ItineraryResponse.model_validate(RESPONSE)

    assert resp.model_dump(mode="json", exclude_none=True) == RESPONSE


def test_schedule_item_mode_rules():
    base = {"time": "10:00", "end_time": "11:00", "title": "x"}
    with pytest.raises(ValidationError, match="place"):
        ScheduleItem.model_validate({**base, "mode": "common"})
    with pytest.raises(ValidationError, match="picked_by"):
        ScheduleItem.model_validate({**base, "mode": "alternate", "place": SENSOJI})
    with pytest.raises(ValidationError, match="2개 이상"):
        ScheduleItem.model_validate({**base, "mode": "separate", "separate": []})
    with pytest.raises(ValidationError):
        ScheduleItem.model_validate({**base, "time": "9:00", "mode": "common", "place": SENSOJI})


def test_participant_answers_to_selections():
    p = Participant.model_validate({"id": "me", "name": "나", "answers": [
        {"question_key": "Q_FOOD", "selected_option_keys": ["CAFE_TOUR"]},
        {"question_key": "Q_TIME", "selected_option_keys": []}]})
    assert p.quiz_version == "v1.0"
    assert p.selections() == {"Q_FOOD": ["CAFE_TOUR"], "Q_TIME": []}


def test_participant_rejects_duplicate_question_key():
    answer = {"question_key": "Q_FOOD", "selected_option_keys": ["CAFE_TOUR"]}
    with pytest.raises(ValidationError, match="중복"):
        Participant.model_validate({"id": "me", "name": "나", "answers": [answer, answer]})


def test_special_requests_max_1000():
    with pytest.raises(ValidationError):
        ItineraryRequest.model_validate({**REQUEST, "special_requests": "가" * 1001})


def test_unknown_option_key_is_rejected():
    with pytest.raises(ValidationError):
        ItineraryRequest.model_validate({**REQUEST, "options": {"maxSeparateBlocksPerDay": 2}})


@pytest.mark.parametrize("extra", [{"specialRequests": "x"}, {"quizVersion": "v1.0"}, {"unknown": 1}])
def test_unknown_top_level_key_is_rejected(extra):
    with pytest.raises(ValidationError):
        ItineraryRequest.model_validate({**REQUEST, **extra})


def test_unknown_participant_key_is_rejected():
    p = {**REQUEST["participants"][0], "quizVersion": "v1.0"}
    with pytest.raises(ValidationError):
        Participant.model_validate(p)
