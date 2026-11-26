import pytest

from travel_ai.places import load_places
from travel_ai.quiz import QUIZ
from travel_ai.taxonomy import CONCEPTS

PLACES = load_places("도쿄")

# 도쿄에서 후보가 1곳뿐인 컨셉 (데이터 보강 시 여기서 빼면 된다)
KNOWN_THIN = {"캠핑", "익스트림", "농촌·생활"}


def test_ids_unique_and_fields_present():
    ids = [p["id"] for p in PLACES]
    assert len(ids) == len(set(ids))
    for p in PLACES:
        assert {"id", "name", "area", "lat", "lng", "concepts", "durationMin"} <= p.keys()
        assert p["concepts"] and p["durationMin"] > 0


def test_concepts_exist_in_taxonomy():
    for p in PLACES:
        assert set(p["concepts"]) <= CONCEPTS.keys(), p["id"]


def test_coordinates_within_tokyo_day_trip_range():
    # 도쿄 도심 + 당일치기 근교(하코네·가마쿠라·이즈오시마)
    for p in PLACES:
        assert 34.5 <= p["lat"] <= 36.0 and 138.9 <= p["lng"] <= 140.1, p["id"]


def test_quiz_concepts_have_enough_candidates():
    quiz_concepts = {concept for question in QUIZ for _, concept in question if concept}
    counts = {c: sum(c in p["concepts"] for p in PLACES) for c in quiz_concepts}

    # 분리/번갈아에서 고를 수 있도록 컨셉당 2곳 이상을 목표로 한다
    thin = {c for c, n in counts.items() if n < 2}
    assert thin == KNOWN_THIN, counts


def test_unknown_city():
    with pytest.raises(ValueError):
        load_places("오사카")
