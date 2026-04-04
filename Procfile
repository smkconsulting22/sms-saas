web: gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
worker: celery -A app.workers.celery_app worker --loglevel=info -P solo