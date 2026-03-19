FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# 시스템 의존성 (psycopg2, curl for healthcheck)
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Python 의존성 (uv 사용)
RUN pip install --no-cache-dir uv

# backend 컨테이너도 루트 의존성 세트를 사용해야 chat orchestrator가 동작한다.
COPY pyproject.toml uv.lock /app/
RUN uv sync --no-dev --frozen

# 비루트 사용자 생성
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser && \
    mkdir -p /app/backend/staticfiles && \
    chown appuser:appuser /app/backend/staticfiles

# 소스 복사
COPY --chown=appuser:appuser backend/ /app/backend/
COPY --chown=appuser:appuser llm/ /app/llm/

# entrypoint
RUN chmod +x /app/backend/entrypoint.sh

USER appuser

WORKDIR /app/backend

EXPOSE 8000

ENTRYPOINT ["/app/backend/entrypoint.sh"]
