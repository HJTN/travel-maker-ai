"""동행자 취향 비교 (S08 이후, 일정 생성 전 단계).

quiz.build_profile 결과를 동행자별로 받아
- 일치도 (concept 집합의 쌍별 Jaccard 평균)
- 공통 컨셉 (모두가 고름) -> 공통 일정 후보
- 다른 컨셉 (일부만 고름) -> mode 로 일정 방식 판정
  퀴즈 단계에서 사용자는 대분류를 모두 고르므로, 차이는 중분류 수준에서 판단한다.
  - alternate (번갈아): 안 고른 사람도 모두 같은 중분류의 다른 소분류를 골랐다.
    중분류 취향은 같으니 시간대별로 서로의 장소를 섞어 함께 간다.
  - separate (분리): 안 고른 사람 중 그 중분류 자체를 고르지 않은 사람이 있다.
    같은 시간대에 각자 다른 장소를 방문한다.
- 대분류별 선호 차이 (클수록 의견 충돌 가능성이 큰 영역)
을 계산한다.
"""

from itertools import combinations

from .taxonomy import CATEGORIES, CONCEPTS


def compare_profiles(profiles: dict[str, dict]) -> dict:
    """profiles: {참여자 id: build_profile 결과}. 참여자는 2명 이상."""
    if len(profiles) < 2:
        raise ValueError("비교하려면 참여자가 2명 이상이어야 합니다.")

    picked = {pid: {c["name"]: c["count"] for c in p["concepts"]} for pid, p in profiles.items()}
    picked_groups = {pid: {CONCEPTS[c][1] for c in counts} for pid, counts in picked.items()}
    all_concepts = set().union(*picked.values())

    def total_count(concept: str) -> int:
        return sum(counts.get(concept, 0) for counts in picked.values())

    ordered = sorted(all_concepts, key=lambda c: (-total_count(c), c))
    common, different = [], []
    for concept in ordered:
        category, group = CONCEPTS[concept]
        liked_by = [pid for pid, counts in picked.items() if concept in counts]
        item = {"name": concept, "category": category, "group": group, "liked_by": liked_by}
        if len(liked_by) == len(picked):
            common.append(item)
        else:
            others = [pid for pid in picked if pid not in liked_by]
            same_group = all(group in picked_groups[pid] for pid in others)
            item["mode"] = "alternate" if same_group else "separate"
            different.append(item)

    category_gaps = []
    for category in CATEGORIES:
        scores = {pid: p["categories"][category] for pid, p in profiles.items()}
        category_gaps.append({"category": category, "scores": scores, "gap": max(scores.values()) - min(scores.values())})
    category_gaps.sort(key=lambda g: -g["gap"])

    return {
        "match_rate": _mean_pairwise_jaccard([set(counts) for counts in picked.values()]),
        "common": common,
        "different": different,
        "category_gaps": category_gaps,
    }


def _mean_pairwise_jaccard(sets: list[set]) -> float:
    scores = [len(a & b) / len(a | b) if a | b else 0.0 for a, b in combinations(sets, 2)]
    return sum(scores) / len(scores)
