FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/backend

# 시스템 의존성 (psycopg2, curl for healthcheck)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Python 의존성 (uv 사용)
RUN pip install --no-cache-dir uv
COPY backend/requirements.txt /app/backend/requirements.txt
RUN uv pip install --system --no-cache -r requirements.txt

# 비루트 사용자 생성
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser && \
    mkdir -p /app/backend/staticfiles && \
    chown -R appuser:appuser /app

# 소스 복사
COPY --chown=appuser:appuser backend/ /app/backend/

# entrypoint
RUN chmod +x /app/backend/entrypoint.sh

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/backend/entrypoint.sh"]
