import logging
import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models.campaign import Campaign, CampaignStatus
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignOut
from app.dependencies import get_current_tenant, require_admin
from app.services.campaign import run_campaign
from app.tasks.sms_tasks import launch_campaign_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/campaigns", tags=["Campagnes"])

@router.post("/", response_model=CampaignOut, status_code=201)
def create_campaign(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_tenant)
):
    status_val = "scheduled" if payload.scheduled_at else "draft"
    campaign = Campaign(
        tenant_id=current["tenant_id"],
        name=payload.name,
        message=payload.message,
        scheduled_at=payload.scheduled_at,
        status=status_val,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign

@router.get("/", response_model=List[CampaignOut])
def list_campaigns(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_tenant)
):
    q = db.query(Campaign).filter(Campaign.tenant_id == current["tenant_id"])
    if status:
        q = q.filter(Campaign.status == status)
    return q.order_by(Campaign.created_at.desc()).all()

@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_tenant)
):
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == current["tenant_id"]
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    return campaign

@router.post("/{campaign_id}/launch")
async def launch_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_tenant)
):
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == current["tenant_id"]
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    if campaign.status == CampaignStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Campagne déjà en cours")

    if campaign.scheduled_at and campaign.scheduled_at > datetime.now(timezone.utc):
        launch_campaign_task.apply_async(
            args=[str(campaign.id), current["tenant_id"]],
            eta=campaign.scheduled_at,
        )
        logger.info(
            "Campagne planifiée campaign_id=%s tenant=%s eta=%s",
            campaign_id,
            current["tenant_id"],
            campaign.scheduled_at.isoformat(),
        )
        return {
            "message": f"Campagne planifiée pour le {campaign.scheduled_at.strftime('%d/%m/%Y à %H:%M')}",
            "campaign_id": campaign_id,
        }
    else:
        launch_campaign_task.delay(str(campaign.id), current["tenant_id"])
        logger.info(
            "Campagne lancée immédiatement campaign_id=%s tenant=%s",
            campaign_id,
            current["tenant_id"],
        )
        return {
            "message": "Campagne lancée en arrière-plan",
            "campaign_id": campaign_id,
        }
    
    
@router.patch("/{campaign_id}", response_model=CampaignOut)
def update_campaign(
    campaign_id: str,
    payload: CampaignUpdate,
    db: Session = Depends(get_db),
    current: dict = Depends(require_admin),
):
    try:
        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.tenant_id == current["tenant_id"],
        ).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campagne introuvable")
        if campaign.status not in ("draft", "scheduled"):
            raise HTTPException(
                status_code=400,
                detail=f"Impossible de modifier une campagne au statut '{campaign.status}' (draft ou scheduled requis)",
            )
        if payload.name is not None:
            campaign.name = payload.name
        if payload.message is not None:
            campaign.message = payload.message
        if payload.scheduled_at is not None:
            campaign.scheduled_at = payload.scheduled_at
            campaign.status = "scheduled"
        db.commit()
        db.refresh(campaign)
        logger.info("Campagne modifiée campaign_id=%s tenant=%s", campaign_id, current["tenant_id"])
        return campaign
    except HTTPException:
        raise
    except Exception:
        logger.error(
            "Erreur PATCH campagne campaign_id=%s tenant=%s :\n%s",
            campaign_id, current.get("tenant_id"), traceback.format_exc(),
        )
        raise HTTPException(status_code=500, detail="Erreur lors de la modification de la campagne")


@router.post("/{campaign_id}/relaunch")
def relaunch_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current: dict = Depends(require_admin),
):
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == current["tenant_id"],
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    if campaign.status != "failed":
        raise HTTPException(
            status_code=400,
            detail=f"Seules les campagnes en échec peuvent être relancées (statut actuel : '{campaign.status}')",
        )
    campaign.status = "draft"
    db.commit()
    db.refresh(campaign)
    launch_campaign_task.delay(str(campaign.id), current["tenant_id"])
    logger.info("Campagne relancée campaign_id=%s tenant=%s", campaign_id, current["tenant_id"])
    return campaign


@router.delete("/{campaign_id}")
def delete_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_tenant)
):
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == current["tenant_id"]
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    if campaign.status == CampaignStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Impossible de supprimer une campagne en cours")
    db.delete(campaign)
    db.commit()
    return {"message": "Campagne supprimée"}