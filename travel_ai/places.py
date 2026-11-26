"""도시별 장소 후보 데이터.

일정 생성 시 LLM 은 이 후보 안에서만 장소를 고른다 (없는 장소를 지어내지 않게 하기 위함).
가게 단위가 아니라 명소·거리·지역 단위로 모았다.
좌표는 수작업 입력값이라 대략적이며, 이후 지도 API 로 검증·보강이 필요하다.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
CITY_FILES = {"도쿄": "tokyo_places.json"}


def load_places(city: str) -> list[dict]:
    """city: 요청의 city 값 (예: "도쿄")."""
    if city not in CITY_FILES:
        raise ValueError(f"지원하지 않는 도시입니다: {city}")
    return json.loads((DATA_DIR / CITY_FILES[city]).read_text(encoding="utf-8"))
