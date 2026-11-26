import pytest

from travel_ai.compare import compare_profiles
from travel_ai.quiz import build_profile

# 나: 산(트레킹), 카페 투어, 온천 / 동행자: 카페 투어, 쇼핑, 온천
ME = build_profile({"0": [0], "3": [2], "8": [1]})
FRIEND = build_profile({"3": [2], "7": [0], "8": [1]})


def test_common_and_different():
    result = compare_profiles({"me": ME, "friend": FRIEND})

    assert [c["name"] for c in result["common"]] == ["온천·스파", "카페 투어"]
    assert result["common"][0]["liked_by"] == ["me", "friend"]
    assert {c["name"]: c["liked_by"] for c in result["different"]} == {
        "트레킹·등산": ["me"],
        "쇼핑 유형": ["friend"],
    }


def test_different_group_is_separate():
    # 트레킹(자연 경관)·쇼핑(쇼핑·시장 구경): 상대는 그 중분류를 하나도 안 고름
    result = compare_profiles({"me": ME, "friend": FRIEND})
    assert {c["name"]: c["mode"] for c in result["different"]} == {"트레킹·등산": "separate", "쇼핑 유형": "separate"}


def test_same_category_different_group_is_separate():
    # 둘 다 미식이지만 카페·디저트 vs 길거리 음식·시장 -> 중분류가 달라 분리
    cafe = build_profile({"3": [2]})
    market = build_profile({"3": [3]})
    result = compare_profiles({"a": cafe, "b": market})
    assert {c["name"]: c["mode"] for c in result["different"]} == {"카페 투어": "separate", "시장 먹거리": "separate"}


def test_same_group_different_concept_is_alternate():
    # 둘 다 역사·문화 유적이지만 유적지 vs 전시 -> 번갈아
    heritage = build_profile({"1": [1]})
    exhibition = build_profile({"2": [0]})
    result = compare_profiles({"a": heritage, "b": exhibition})
    assert result["different"][0]["group"] == "역사·문화 유적"
    assert {c["name"]: c["mode"] for c in result["different"]} == {"유적지": "alternate", "전시": "alternate"}


def test_separate_if_any_non_picker_lacks_group():
    # c는 역사·문화 유적을 안 고름 -> b가 전시를 골랐어도 유적지는 분리
    heritage = build_profile({"1": [1]})
    exhibition = build_profile({"2": [0]})
    landmark = build_profile({"1": [0]})
    result = compare_profiles({"a": heritage, "b": exhibition, "c": landmark})
    assert {c["name"]: c["mode"] for c in result["different"]}["유적지"] == "separate"


def test_common_has_no_mode():
    result = compare_profiles({"me": ME, "friend": FRIEND})
    assert all("mode" not in c for c in result["common"])


def test_match_rate_is_jaccard():
    # 교집합 2개 / 합집합 4개
    assert compare_profiles({"me": ME, "friend": FRIEND})["match_rate"] == 0.5
    assert compare_profiles({"me": ME, "copy": ME})["match_rate"] == 1.0


def test_category_gaps_sorted_desc():
    gaps = compare_profiles({"me": ME, "friend": FRIEND})["category_gaps"]

    assert [g["gap"] for g in gaps] == sorted((g["gap"] for g in gaps), reverse=True)
    by_category = {g["category"]: g for g in gaps}
    assert by_category["관광"]["scores"] == {"me": pytest.approx(1 / 3), "friend": 0.0}
    assert by_category["미식"]["gap"] == 0.0


def test_three_people_common_requires_everyone():
    third = build_profile({"3": [2]})
    result = compare_profiles({"me": ME, "friend": FRIEND, "third": third})

    assert [c["name"] for c in result["common"]] == ["카페 투어"]
    assert result["match_rate"] == pytest.approx((0.5 + 1 / 3 + 1 / 3) / 3)


def test_requires_two_people():
    with pytest.raises(ValueError):
        compare_profiles({"me": ME})
