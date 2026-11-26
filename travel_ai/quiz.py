"""S03 사진 퀴즈 응답 -> S04 취향 프로필.

퀴즈 문항·선택지 순서는 gdg-frontend/src/App.jsx 의 quizQuestions 와 같다.
각 선택지는 컨셉 소분류(taxonomy.CONCEPTS) 하나에 대응한다.
6번 문항(숙소)은 컨셉이 아니라 숙소 선호로 따로 모은다.
"""

from collections import Counter

from .taxonomy import CATEGORIES, CONCEPTS

LODGING_QUESTION = 5

QUIZ: list[list[tuple[str, str | None]]] = [
    # (선택지 라벨, 소분류)
    [("산", "트레킹·등산"), ("캠핑", "캠핑"), ("바다", "해변"), ("도심", "로컬 산책")],
    [("랜드마크", "대표 명소"), ("유적지", "유적지"), ("자연경관", "계절 경관"), ("섬", "섬")],
    [("전시관람", "전시"), ("트레킹·등산", "트레킹·등산"), ("촬영지 탐방", "촬영지 탐방"), ("야경", "대표 명소")],
    [("로컬 음식", "로컬 음식"), ("파인다이닝", "파인다이닝"), ("카페 투어", "카페 투어"), ("시장 먹거리", "시장 먹거리")],
    [("로컬 술집", "술 여행"), ("와인바", "술 여행"), ("로컬 식당", "로컬 음식"), ("야시장", "시장 먹거리")],
    [("캠핑장", None), ("호텔·리조트", None), ("게스트하우스", None), ("가성비 숙소", None)],
    [("지역 축제", "지역 축제"), ("공예 만들기", "만들기"), ("익스트림 스포츠", "익스트림"), ("농촌 체험", "농촌·생활")],
    [("쇼핑", "쇼핑 유형"), ("공연 관람", "공연 관람"), ("물놀이", "물놀이"), ("골목 산책", "로컬 산책")],
    [("명상·리트릿", "명상·리트릿"), ("온천·스파", "온천·스파"), ("동물 교감", "놀이시설"), ("놀이시설", "놀이시설")],
]


def build_profile(selections: dict) -> dict:
    """프론트 quizSelections ({문항 인덱스: [선택지 인덱스, ...]}) 로 취향 프로필을 만든다.

    JSON 을 거치면 키가 문자열("0")이 되므로 int 로 바꿔 읽는다.
    """
    concept_counts: Counter[str] = Counter()
    lodging: list[str] = []

    for question_key, option_indexes in selections.items():
        question = QUIZ[int(question_key)]
        for option_index in option_indexes:
            label, concept = question[option_index]
            if int(question_key) == LODGING_QUESTION:
                lodging.append(label)
            else:
                concept_counts[concept] += 1

    category_counts = Counter({category: 0 for category in CATEGORIES})
    for concept, count in concept_counts.items():
        category_counts[CONCEPTS[concept][0]] += count
    total = sum(category_counts.values())

    return {
        "categories": {c: (category_counts[c] / total if total else 0.0) for c in CATEGORIES},
        "concepts": [
            {"name": concept, "category": CONCEPTS[concept][0], "group": CONCEPTS[concept][1], "count": count}
            for concept, count in concept_counts.most_common()
        ],
        "lodging": lodging,
    }
