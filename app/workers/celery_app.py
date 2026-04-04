from celery import Celery
from app.config import settings

celery_app = Celery(
    "sms_saas",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.sms_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Abidjan",
    enable_utc=True,
    # Retry automatique en cas d'échec
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)