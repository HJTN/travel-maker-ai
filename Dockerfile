FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 의존성을 먼저 설치해 코드만 바뀔 때 레이어 캐시를 재사용한다
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY travel_ai/ travel_ai/

# Cloud Run은 PORT 환경변수로 포트를 알려준다
CMD ["sh", "-c", "uvicorn travel_ai.api:app --host 0.0.0.0 --port ${PORT:-8080}"]
