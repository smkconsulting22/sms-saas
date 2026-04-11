import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from app.database import get_db
from app.models.campaign import Campaign, CampaignStatus
from app.schemas.campaign import CampaignCreate, CampaignOut
from app.dependencies import get_current_tenant
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
    campaign = Campaign(
        tenant_id=current["tenant_id"],
        name=payload.name,
        message=payload.message,
        scheduled_at=payload.scheduled_at
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign

@router.get("/", response_model=List[CampaignOut])
def list_campaigns(
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_tenant)
):
    return db.query(Campaign).filter(
        Campaign.tenant_id == current["tenant_id"]
    ).order_by(Campaign.created_at.desc()).all()

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