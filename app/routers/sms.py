import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.sms import SMSSend, SMSResponse
from app.services.orange_sms import send_sms
from app.models.credit import CreditBalance
from app.models.campaign import CampaignLog
from app.dependencies import get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sms", tags=["SMS"])

# Correspondance statuts Orange → statuts internes
_ORANGE_STATUS_MAP = {
    "DeliveredToTerminal": "delivered",
    "DeliveryUncertain": "uncertain",
    "DeliveryImpossible": "failed",
    "MessageExpired": "failed",
    "MessageWaiting": "pending",
}


@router.post("/send", response_model=SMSResponse)
async def send_single_sms(
    payload: SMSSend,
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_tenant),
):
    tenant_id = current["tenant_id"]

    balance = db.query(CreditBalance).filter(
        CreditBalance.tenant_id == tenant_id
    ).first()

    if not balance or balance.balance < 1:
        logger.warning("Crédits insuffisants pour envoi SMS tenant=%s", tenant_id)
        raise HTTPException(status_code=402, detail="Crédits insuffisants")

    try:
        result = await send_sms(payload.recipient, payload.message, tenant_id=tenant_id)

        balance.balance -= 1
        db.commit()

        resource_url = result.get("outboundSMSMessageRequest", {}).get("resourceURL", "")
        message_id = resource_url.split("/")[-1] if resource_url else None

        logger.info(
            "SMS envoyé tenant=%s recipient=%s message_id=%s",
            tenant_id,
            payload.recipient,
            message_id,
        )
        return SMSResponse(
            status="sent",
            recipient=payload.recipient,
            message_id=message_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Erreur envoi SMS tenant=%s recipient=%s : %s", tenant_id, payload.recipient, e)
        raise HTTPException(status_code=500, detail=f"Erreur Orange API : {str(e)}")


@router.post("/delivery-report", status_code=200)
async def delivery_report(request: Request, db: Session = Depends(get_db)):
    """Webhook public Orange pour les rapports de livraison SMS.
    Pas d'authentification JWT — appelé directement par Orange.
    """
    try:
        body = await request.json()
    except Exception:
        logger.warning("Delivery report reçu avec corps invalide")
        return {"status": "ignored"}

    logger.info("Delivery report reçu : %s", str(body)[:300])

    # Extraire messageId et deliveryStatus depuis le format Orange
    try:
        notification = body.get("deliveryInfoNotification", {})
        delivery_info = notification.get("deliveryInfo", {})
        message_id = delivery_info.get("messageId") or notification.get("messageId")
        orange_status = delivery_info.get("deliveryStatus") or notification.get("deliveryStatus")
    except Exception:
        logger.warning("Delivery report : impossible de parser le body — %s", str(body)[:200])
        return {"status": "ignored"}

    if not message_id:
        logger.warning("Delivery report sans messageId — ignoré")
        return {"status": "ignored"}

    internal_status = _ORANGE_STATUS_MAP.get(orange_status, orange_status)

    # Mettre à jour le ou les CampaignLog correspondants
    logs = db.query(CampaignLog).filter(CampaignLog.message_id == message_id).all()
    if not logs:
        logger.warning("Delivery report : aucun log trouvé pour message_id=%s", message_id)
        return {"status": "not_found", "message_id": message_id}

    for log in logs:
        log.status = internal_status

    db.commit()

    logger.info(
        "Delivery report traité : message_id=%s orange_status=%s → internal=%s (%d log(s) mis à jour)",
        message_id,
        orange_status,
        internal_status,
        len(logs),
    )
    return {"status": "ok", "message_id": message_id, "delivery_status": internal_status}
