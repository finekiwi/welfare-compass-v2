#!/bin/bash
set -e

PYTHON_BIN="/app/.venv/bin/python"

echo "⏳ Waiting for DB ($DB_HOST:$DB_PORT)..."
while ! "$PYTHON_BIN" -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(1)
s.connect(('${DB_HOST:-db}', ${DB_PORT:-5432}))
s.close()
" 2>/dev/null; do
  sleep 1
done
echo "✅ DB ready"

echo "🔄 Running migrations..."
"$PYTHON_BIN" manage.py migrate --noinput

echo "🔄 Collecting static files..."
"$PYTHON_BIN" manage.py collectstatic --noinput

echo "🚀 Starting gunicorn..."
exec "$PYTHON_BIN" -m gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 1 \
  --threads 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
