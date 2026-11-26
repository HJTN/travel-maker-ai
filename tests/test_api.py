import asyncio
import copy
import json

import pytest
from fastapi.testclient import TestClient
from langchain_core.exceptions import ModelAPIError, ModelAuthenticationError

from travel_ai import api
from travel_ai.api import app, get_llm
from test_generator import GOOD, REQUEST, fake

BODY = REQUEST.model_dump(mode="json", by_alias=True)


class Raising:
    def __init__(self, error):
        self.error = error

    async def ainvoke(self, messages):
        raise self.error


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def use(llm):
    app.dependency_overrides[get_llm] = lambda: llm


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_creates_itinerary_in_snake_case(client):
    use(fake(GOOD))
    res = client.post("/itineraries", json=BODY)

    assert res.status_code == 200
    first = res.json()["days"][0]["schedule"][0]
    assert first["picked_by"] == ["me"] and first["end_time"] == "11:30"
    assert first["place"]["name"] == "센소지"  # 후보 데이터로 덮어쓴 값
    assert "separate" not in first  # null 필드는 빼고 보낸다


def test_invalid_request_is_422(client):
    use(fake(GOOD))
    res = client.post("/itineraries", json={**BODY, "conditions": {**BODY["conditions"], "tempo": "아주 바쁨"}})
    assert res.status_code == 422


@pytest.mark.parametrize("llm, status, code, retryable", [
    (fake("not json", "not json", "not json"), 502, "GENERATION_FAILED", True),
    (Raising(ModelAPIError("503 UNAVAILABLE")), 503, "LLM_UNAVAILABLE", True),
    (Raising(ModelAuthenticationError("bad key")), 500, "LLM_ERROR", False),
])
def test_failures_map_to_s09_errors(client, llm, status, code, retryable):
    use(llm)
    res = client.post("/itineraries", json=BODY)

    assert res.status_code == status
    assert res.json()["code"] == code and res.json()["retryable"] is retryable


def test_unsupported_city(client):
    use(fake(GOOD))
    res = client.post("/itineraries", json={**BODY, "city": "오사카"})

    assert res.status_code == 400
    assert res.json() | {"message": ""} == {"code": "UNSUPPORTED_CITY", "message": "", "retryable": False}


def test_unknown_quiz_key_is_422(client):
    use(fake(GOOD))
    bad = copy.deepcopy(BODY)
    bad["participants"][0]["answers"][0]["selected_option_keys"] = ["SCENIC_PHOTO"]
    res = client.post("/itineraries", json=bad)

    assert res.status_code == 422
    assert "SCENIC_PHOTO" in res.text


def test_unknown_question_key_with_empty_options_is_422(client):
    use(fake(GOOD))
    bad = copy.deepcopy(BODY)
    bad["participants"][0]["answers"].append({"question_key": "Q_BOGUS", "selected_option_keys": []})
    res = client.post("/itineraries", json=bad)

    assert res.status_code == 422
    assert "Q_BOGUS" in res.text


def test_camel_case_key_is_422(client):
    use(fake(GOOD))
    res = client.post("/itineraries", json={**BODY, "specialRequests": "x"})
    assert res.status_code == 422


def test_unknown_option_key_is_422(client):
    use(fake(GOOD))
    res = client.post("/itineraries", json={**BODY, "options": {"maxSeparateBlocksPerDay": 2}})
    assert res.status_code == 422


class Slow:
    async def ainvoke(self, messages):
        await asyncio.sleep(1)


def test_generation_timeout_is_503(client, monkeypatch):
    monkeypatch.setattr(api, "GENERATION_TIMEOUT_SECONDS", 0.05)
    use(Slow())
    res = client.post("/itineraries", json=BODY)

    assert res.status_code == 503
    assert res.json()["code"] == "LLM_UNAVAILABLE" and res.json()["retryable"] is True
