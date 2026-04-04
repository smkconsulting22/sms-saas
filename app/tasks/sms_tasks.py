from celery import shared_task
from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.services.campaign import run_campaign
import asyncio

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def launch_campaign_task(self, campaign_id: str, tenant_id: str):
    """Tâche Celery pour lancer une campagne (sync wrapper)"""
    try:
        db = SessionLocal()
        asyncio.run(run_campaign(db, campaign_id, tenant_id))
        db.close()
    except Exception as exc:
        db.close()
        raise self.retry(exc=exc)