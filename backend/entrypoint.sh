#!/bin/bash
set -e

echo "⏳ Waiting for DB ($DB_HOST:$DB_PORT)..."
while ! python -c "
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
python manage.py migrate --noinput

echo "🔄 Collecting static files..."
python manage.py collectstatic --noinput

echo "🚀 Starting gunicorn..."
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --timeout 120
