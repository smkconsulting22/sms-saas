#!/bin/bash
set -e

echo "==> Lancement des migrations Alembic..."
alembic upgrade head

echo "==> Démarrage de Gunicorn..."
exec gunicorn app.main:app \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT:-8000} \
    --timeout 120 \
    --keep-alive 5 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
