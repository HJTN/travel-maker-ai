"""AI 일정 생성 HTTP API.

BE(여행 일정 관리 API)가 서버 간 호출로 쓴다: 동행자 전원의 퀴즈 응답과 S05 조건을 모아 보내면
S10 에 보여줄 일정을 돌려준다. 실패하면 ErrorResponse 로 S09 에서 재시도할지 알려준다.

실행: uvicorn travel_ai.api:app --reload   (저장소 루트에서, .env 에 GOOGLE_API_KEY 필요)
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from langchain_core.exceptions import ModelError

from .generator import ItineraryGenerationError, generate_itinerary
from .places import CITY_FILES
from .schemas import ErrorResponse, ItineraryRequest, ItineraryResponse

load_dotenv()

app = FastAPI(title="Travel Maker AI")


@lru_cache
def get_llm():
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
        temperature=0.7,
        response_mime_type="application/json",
    )


def _error(status: int, code: str, message: str, retryable: bool) -> JSONResponse:
    body = ErrorResponse(code=code, message=message, retryable=retryable)
    return JSONResponse(status_code=status, content=body.model_dump(by_alias=True))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post(
    "/itineraries",
    response_model=ItineraryResponse,
    response_model_exclude_none=True,
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def create_itinerary(request: ItineraryRequest, llm=Depends(get_llm)):
    if request.city not in CITY_FILES:
        return _error(400, "UNSUPPORTED_CITY", f"지원하지 않는 도시입니다: {request.city} (지원: {', '.join(CITY_FILES)})", False)
    try:
        return await generate_itinerary(request, llm)
    except ItineraryGenerationError as e:
        # LLM 이 재시도 후에도 규칙에 맞는 일정을 못 만듦. 다시 생성하면 될 수 있다.
        return _error(502, "GENERATION_FAILED", f"일정을 만들지 못했습니다: {e}", True)
    except ModelError as e:
        # Gemini 쪽 오류. 과부하(503)·한도 초과(429)·타임아웃은 재시도 가능, 인증·요청 오류는 아니다.
        if getattr(e, "is_retryable", False):
            return _error(503, "LLM_UNAVAILABLE", "AI 모델이 일시적으로 응답하지 않습니다. 잠시 후 다시 시도해 주세요.", True)
        return _error(500, "LLM_ERROR", f"AI 모델 호출에 실패했습니다: {type(e).__name__}", False)
