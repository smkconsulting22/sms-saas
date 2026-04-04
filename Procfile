web: bash start.sh
worker: celery -A app.workers.celery_app worker --loglevel=info -P solo
