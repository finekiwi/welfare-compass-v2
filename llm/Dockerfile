FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 시스템 의존성 (빌드 도구, curl for healthcheck)
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# uv 설치
RUN pip install --no-cache-dir uv

# 의존성 설치 (루트 pyproject.toml + uv.lock 사용)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

# 비루트 사용자 생성
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser && \
    chown -R appuser:appuser /app

# 소스 복사
COPY --chown=appuser:appuser llm/ /app/llm/

USER appuser

EXPOSE 8001

CMD ["uv", "run", "python", "-m", "llm.mcp.server"]
