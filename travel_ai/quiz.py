"""S03 사진 퀴즈 응답 -> S04 취향 프로필.

퀴즈 문항·선택지 키는 BE 위키 API-Spec 퀴즈 기준표 v1.0 과 같다.
각 선택지는 컨셉 소분류(taxonomy.CONCEPTS) 하나에 대응한다.
Q_ACCOMMODATION(숙소) 문항은 컨셉이 아니라 숙소 선호로 따로 모은다.
"""

from collections import Counter

from .taxonomy import CATEGORIES, CONCEPTS

LODGING_QUESTION = "Q_ACCOMMODATION"

# {문항 키: {선택지 키: (선택지 라벨, 소분류)}}. 문항 순서는 화면 노출 순서다.
QUIZ: dict[str, dict[str, tuple[str, str | None]]] = {
    "Q_DESTINATION": {
        "MOUNTAIN": ("산", "트레킹·등산"), "CAMPING": ("캠핑", "캠핑"),
        "SEA": ("바다", "해변"), "CITY": ("도심", "로컬 산책"),
    },
    "Q_PLACE": {
        "LANDMARK": ("랜드마크", "대표 명소"), "HISTORIC_SITE": ("유적지", "유적지"),
        "SCENIC_VIEW": ("풍경명소", "계절 경관"), "ISLAND": ("섬", "섬"),
    },
    "Q_TIME": {
        "EXHIBITION": ("전시관람", "전시"), "TREKKING": ("트레킹·등산", "트레킹·등산"),
        "SCENIC_TRAIN": ("풍경열차탐방", "계절 경관"), "NIGHT_VIEW": ("야경", "대표 명소"),
    },
    "Q_FOOD": {
        "LOCAL_FOOD": ("로컬음식", "로컬 음식"), "FINE_DINING": ("파인다이닝", "파인다이닝"),
        "CAFE_TOUR": ("카페 투어", "카페 투어"), "MARKET_FOOD": ("시장먹거리", "시장 먹거리"),
    },
    "Q_EVENING": {
        "LOCAL_PUB": ("전통주점", "술 여행"), "WINE_BAR": ("와인바", "술 여행"),
        "LOCAL_RESTAURANT": ("로컬식당", "로컬 음식"), "NIGHT_MARKET": ("야시장", "시장 먹거리"),
    },
    "Q_ACCOMMODATION": {
        "CAMPGROUND": ("캠핑장", None), "HOTEL_RESORT": ("호텔·리조트", None),
        "GUESTHOUSE": ("게스트하우스", None), "CAPSULE_HOTEL": ("캡슐호텔", None),
    },
    "Q_EXPERIENCE": {
        "LOCAL_FESTIVAL": ("지역 축제", "지역 축제"), "CRAFT_MAKING": ("공예만들기", "만들기"),
        "EXTREME_SPORTS": ("익스트림스포츠", "익스트림"), "RURAL_EXPERIENCE": ("농촌체험", "농촌·생활"),
    },
    "Q_FREE_TIME": {
        "SHOPPING": ("쇼핑", "쇼핑 유형"), "PERFORMANCE": ("공연 관람", "공연 관람"),
        "WATER_PLAY": ("물놀이", "물놀이"), "ALLEY_WALK": ("골목 산책", "로컬 산책"),
    },
    "Q_RELAXATION": {
        "MEDITATION_YOGA": ("명상·요가", "명상·리트릿"), "HOT_SPRING_SPA": ("온천·스파", "온천·스파"),
        "ANIMAL_INTERACTION": ("동물 교감", "놀이시설"), "THEME_PARK": ("테마파크", "놀이시설"),
    },
}


def build_profile(selections: dict[str, list[str]]) -> dict:
    """{문항 키: [선택지 키, ...]} 로 취향 프로필을 만든다.

    모르는 문항·선택지 키는 ValueError. 같은 선택지가 중복되면 한 번만 센다.
    """
    concept_counts: Counter[str] = Counter()
    lodging: list[str] = []

    for question_key, option_keys in selections.items():
        if question_key not in QUIZ:  # 선택지가 비어 있어도 문항 키는 검사한다
            raise ValueError(f"알 수 없는 퀴즈 키: {question_key}")
        for option_key in dict.fromkeys(option_keys):
            try:
                label, concept = QUIZ[question_key][option_key]
            except KeyError:
                raise ValueError(f"알 수 없는 퀴즈 키: {question_key} / {option_key}") from None
            if question_key == LODGING_QUESTION:
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
