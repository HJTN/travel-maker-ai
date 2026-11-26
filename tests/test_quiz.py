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


def test_quiz_shape_and_concepts_exist():
    assert len(QUIZ) == 9
    for question in QUIZ:
        assert len(question) == 4
        for _, concept in question:
            assert concept is None or concept in CONCEPTS


def test_build_profile_counts_and_ratios():
    # 프론트에서 JSON 으로 넘어오면 키가 문자열이다.
    profile = build_profile({"0": [0], "2": [1, 3], "3": [2], "5": [1]})

    assert profile["concepts"][0] == {"name": "트레킹·등산", "category": "관광", "group": "자연 경관", "count": 2}
    assert {c["name"] for c in profile["concepts"]} == {"트레킹·등산", "대표 명소", "카페 투어"}
    assert profile["categories"] == {"관광": 0.75, "미식": 0.25, "휴식": 0.0, "체험": 0.0}
    assert profile["lodging"] == ["호텔·리조트"]


def test_build_profile_empty():
    profile = build_profile({})
    assert profile["concepts"] == []
    assert sum(profile["categories"].values()) == 0


def test_build_profile_rejects_unknown_option():
    with pytest.raises(IndexError):
        build_profile({"0": [4]})
