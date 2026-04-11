import logging
import asyncio
from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.services.campaign import run_campaign

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def launch_campaign_task(self, campaign_id: str, tenant_id: str):
    """Tâche Celery pour lancer une campagne (sync wrapper autour du code async)."""
    logger.info(
        "Lancement campagne campaign_id=%s tenant_id=%s (tentative %d/%d)",
        campaign_id,
        tenant_id,
        self.request.retries + 1,
        self.max_retries + 1,
    )
    db = SessionLocal()
    try:
        asyncio.run(run_campaign(db, campaign_id, tenant_id))
        logger.info("Campagne terminée campaign_id=%s tenant_id=%s", campaign_id, tenant_id)
    except Exception as exc:
        logger.error(
            "Erreur campagne campaign_id=%s tenant_id=%s : %s",
            campaign_id,
            tenant_id,
            str(exc),
        )
        raise self.retry(exc=exc)
    finally:
        db.close()
