from pathlib import Path

import openpyxl
import pytest

from travel_ai.quiz import QUIZ, build_profile
from travel_ai.taxonomy import CONCEPTS

XLSX = Path(__file__).parents[1] / "docs" / "core-documents" / "travel-concept-quiz-class.xlsx"


def test_taxonomy_matches_xlsx():
    sheet = openpyxl.load_workbook(XLSX)["컨셉 분류"]
    rows = {r[2]: (r[0], r[1]) for r in sheet.iter_rows(min_row=2, values_only=True) if r[2]}
    assert rows == CONCEPTS


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


def test_build_profile_empty():
    profile = build_profile({})
    assert profile["concepts"] == []
    assert sum(profile["categories"].values()) == 0


def test_build_profile_rejects_unknown_key():
    with pytest.raises(ValueError, match="Q_DESTINATION / VOLCANO"):
        build_profile({"Q_DESTINATION": ["VOLCANO"]})
