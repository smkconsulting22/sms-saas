from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.sms import SMSSend, SMSResponse
from app.services.orange_sms import send_sms
from app.models.credit import CreditBalance
from app.dependencies import get_current_tenant

router = APIRouter(prefix="/sms", tags=["SMS"])

@router.post("/send", response_model=SMSResponse)
async def send_single_sms(
    payload: SMSSend,
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_tenant)
):
    tenant_id = current["tenant_id"]

    # Vérifier le solde crédits
    balance = db.query(CreditBalance).filter(
        CreditBalance.tenant_id == tenant_id
    ).first()

    if not balance or balance.balance < 1:
        raise HTTPException(status_code=402, detail="Crédits insuffisants")

    try:
        result = await send_sms(payload.recipient, payload.message)

        # Déduire 1 crédit
        balance.balance -= 1
        db.commit()

        resource_url = result.get("outboundSMSMessageRequest", {}).get("resourceURL", "")
        message_id = resource_url.split("/")[-1] if resource_url else None

        return SMSResponse(
            status="sent",
            recipient=payload.recipient,
            message_id=message_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Orange API : {str(e)}")

