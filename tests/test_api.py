import json

import pytest
from fastapi.testclient import TestClient
from langchain_core.exceptions import ModelAPIError, ModelAuthenticationError

from travel_ai.api import app, get_llm
from test_generator import GOOD, REQUEST, fake

BODY = REQUEST.model_dump(mode="json", by_alias=True)


class Raising:
    def __init__(self, error):
        self.error = error

    def invoke(self, messages):
        raise self.error


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def use(llm):
    app.dependency_overrides[get_llm] = lambda: llm


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_creates_itinerary_in_camel_case(client):
    use(fake(GOOD))
    res = client.post("/itineraries", json=BODY)

    assert res.status_code == 200
    first = res.json()["days"][0]["schedule"][0]
    assert first["pickedBy"] == ["me"] and first["endTime"] == "11:30"
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
