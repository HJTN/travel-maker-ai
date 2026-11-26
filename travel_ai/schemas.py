"""AI 일정 생성 API 입출력 형식.

JSON 키는 BE API 와 같은 snake_case 로 주고받는다 (Python 필드명 그대로).
출력 구조는 gdg-frontend/src/data/mockItinerary.js 와 docs/assets 화면 시안을 기준으로 한다.
"""

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .quiz import build_profile


class _Model(BaseModel):
    """API 입출력 모델의 공통 부모."""


# ---------- 입력 ----------

# 입력 모델은 모르는 키를 422로 거부한다. camelCase 키나 오타가 조용히 기본값으로 처리되는 것을 막기 위해서다.
# (출력 모델은 LLM 출력 검증용이라 forbid 하지 않는다.)
_FORBID_EXTRA = ConfigDict(extra="forbid")

# 선택지 문자열은 프론트 S05 화면(App.jsx)의 버튼 라벨과 같다.
Companion = Literal["혼자", "연인", "가족", "친구", "동료"]
Transport = Literal["대중교통", "도보", "기차", "비행기", "렌트카"]
Budget = Literal["50만원 이하", "50만원-100만원", "100만원-200만원", "200만원-300만원", "300만원 이상"]
Tempo = Literal["여유", "조금 여유", "적당히", "조금 바쁨", "바쁨"]


class QuizAnswer(_Model):
    model_config = _FORBID_EXTRA

    # BE 위키 퀴즈 기준표 v1.0 의 문항·선택지 키 (quiz.QUIZ 참고)
    question_key: str
    selected_option_keys: list[str]


class Participant(_Model):
    model_config = _FORBID_EXTRA

    id: str
    name: str
    quiz_version: Literal["v1.0"] = "v1.0"
    answers: list[QuizAnswer]

    @model_validator(mode="after")
    def _check_answers(self) -> "Participant":
        keys = [a.question_key for a in self.answers]
        if len(keys) != len(set(keys)):
            dup = next(k for k in keys if keys.count(k) > 1)
            raise ValueError(f"퀴즈 문항 키가 중복되었습니다: {dup}")
        build_profile(self.selections())  # 모르는 키면 ValueError
        return self

    def selections(self) -> dict[str, list[str]]:
        """build_profile 에 넘기는 {문항 키: [선택지 키, ...]} 형태."""
        return {a.question_key: a.selected_option_keys for a in self.answers}


class TripConditions(_Model):
    model_config = _FORBID_EXTRA

    companion: Companion
    transport: Transport
    budget: Budget
    tempo: Tempo


class GenerationOptions(_Model):
    model_config = _FORBID_EXTRA

    # 분리 일정이 너무 많아지지 않도록 하루에 둘 수 있는 분리 구간 수
    max_separate_blocks_per_day: int = Field(default=1, ge=0)


class ItineraryRequest(_Model):
    model_config = _FORBID_EXTRA

    destination: str = "일본"
    city: str
    start_date: dt.date
    end_date: dt.date
    participants: list[Participant] = Field(min_length=1)
    conditions: TripConditions
    options: GenerationOptions = GenerationOptions()
    special_requests: str | None = Field(default=None, max_length=1000)

    @field_validator("special_requests")
    @classmethod
    def _blank_to_none(cls, v: str | None) -> str | None:
        # 공백만 보내면 요청이 없는 것으로 본다 (프롬프트에 빈 요청이 들어가지 않게)
        return v if v and v.strip() else None

    @model_validator(mode="after")
    def _check(self) -> "ItineraryRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date 는 start_date 이후여야 합니다.")
        ids = [p.id for p in self.participants]
        if len(ids) != len(set(ids)):
            raise ValueError("participants 의 id 가 중복됩니다.")
        return self


# ---------- 출력 ----------

ScheduleMode = Literal["common", "separate", "alternate"]


class Place(_Model):
    id: str  # places 데이터의 장소 id
    name: str
    lat: float
    lng: float
    concept: str  # taxonomy.CONCEPTS 의 소분류


class SeparateOption(_Model):
    """분리 일정에서 한 그룹이 가는 곳."""

    participant_ids: list[str] = Field(min_length=1)
    title: str
    place: Place
    description: str
    reason: str  # 이 그룹에게 추천한 이유


class ScheduleItem(_Model):
    time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    title: str
    mode: ScheduleMode
    # common / alternate: 모두 함께 가는 한 장소
    place: Place | None = None
    description: str | None = None
    reason: str | None = None  # 추천 이유 (모두의 예상 만족도 기준)
    # alternate: 이번 구간의 장소를 고른(취향의 주인인) 참여자
    picked_by: list[str] | None = None
    # separate: 그룹별로 나뉘어 가는 곳
    separate: list[SeparateOption] | None = None

    @model_validator(mode="after")
    def _check(self) -> "ScheduleItem":
        if self.mode == "separate":
            if not self.separate or len(self.separate) < 2:
                raise ValueError("separate 일정은 2개 이상의 그룹이 필요합니다.")
        elif self.place is None:
            raise ValueError(f"{self.mode} 일정에는 place 가 필요합니다.")
        if self.mode == "alternate" and not self.picked_by:
            raise ValueError("alternate 일정에는 picked_by 가 필요합니다.")
        return self


class Day(_Model):
    day: int = Field(ge=1)
    date: dt.date
    title: str
    schedule: list[ScheduleItem] = Field(min_length=1)


class ItineraryResponse(_Model):
    destination: str
    city: str
    days: list[Day] = Field(min_length=1)


class ErrorResponse(_Model):
    """일정 생성 실패 응답 (S09 생성 실패/재시도 화면)."""

    code: Literal["UNSUPPORTED_CITY", "GENERATION_FAILED", "LLM_UNAVAILABLE", "LLM_ERROR"]
    message: str
    retryable: bool  # true 면 같은 요청으로 다시 시도해 볼 만하다 (S09 재시도 버튼)
