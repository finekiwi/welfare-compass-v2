#!/bin/bash
#
# ETL 배치 스크립트
# 용도: 온통청년 API에서 정책 데이터를 수집하여 DB에 저장
# 실행: crontab -e → 0 4 * * * /path/to/run_etl_batch.sh
#

# =============================================================================
# 환경 설정 (cron 환경에서도 동작하도록 PATH 명시)
# =============================================================================
export PATH="/Users/junyongan/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

PROJECT_DIR="/Users/junyongan/Desktop/toyproject/4brain-welfare"
LOG_DIR="$PROJECT_DIR/logs"
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/etl_$DATE.log"

# =============================================================================
# 사전 검증
# =============================================================================
# uv 명령어 존재 확인
if ! command -v uv &> /dev/null; then
    echo "[ERROR] uv 명령어를 찾을 수 없습니다." >&2
    exit 1
fi

# 프로젝트 디렉토리 존재 확인
if [ ! -d "$PROJECT_DIR" ]; then
    echo "[ERROR] 프로젝트 디렉토리가 존재하지 않습니다: $PROJECT_DIR" >&2
    exit 1
fi

# =============================================================================
# 실행
# =============================================================================
cd "$PROJECT_DIR" || exit 1
mkdir -p "$LOG_DIR"

echo "=== ETL Started at $(date) ===" >> "$LOG_FILE"
echo "Working directory: $(pwd)" >> "$LOG_FILE"
echo "uv path: $(which uv)" >> "$LOG_FILE"

# ETL 실행 (API → JSON → DB)
uv run python backend/manage.py run_etl >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

# =============================================================================
# 결과 처리
# =============================================================================
if [ $EXIT_CODE -eq 0 ]; then
    echo "=== ETL Success at $(date) ===" >> "$LOG_FILE"
else
    echo "=== ETL Failed with code $EXIT_CODE at $(date) ===" >> "$LOG_FILE"
    # TODO: 실패 시 슬랙/이메일 알림 (MVP 이후)
fi

exit $EXIT_CODE
