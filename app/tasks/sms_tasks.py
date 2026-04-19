import logging
import asyncio
from datetime import datetime, timezone
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


@celery_app.task
def check_scheduled_campaigns():
    """Vérifie toutes les minutes les campagnes planifiées dont l'heure est passée
    et les lance. Passe le statut à 'running' avant d'envoyer la tâche pour éviter
    les doubles lancements en cas de chevauchement de beat."""
    from app.models.campaign import Campaign
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        campaigns = (
            db.query(Campaign)
            .filter(
                Campaign.status == "scheduled",
                Campaign.scheduled_at <= now,
            )
            .all()
        )
        if not campaigns:
            return

        logger.info("Beat: %d campagne(s) planifiée(s) à lancer", len(campaigns))

        for campaign in campaigns:
            # Marquer immédiatement pour éviter un double lancement
            campaign.status = "running"

        db.commit()

        for campaign in campaigns:
            launch_campaign_task.delay(str(campaign.id), str(campaign.tenant_id))
            logger.info(
                "Beat: campagne lancée campaign_id=%s tenant_id=%s",
                campaign.id, campaign.tenant_id,
            )
    except Exception as exc:
        logger.error("Beat check_scheduled_campaigns erreur : %s", str(exc))
    finally:
        db.close()
