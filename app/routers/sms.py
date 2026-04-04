from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from app.database import get_db
from app.schemas.sms import SMSSend, SMSResponse
from app.services.orange_sms import send_sms
from app.models.credit import CreditBalance
from app.config import settings

router = APIRouter(prefix="/sms", tags=["SMS"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_tenant(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")

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

@router.post("/credits/add-test")
def add_test_credits(
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_tenant)
):
    """Endpoint temporaire pour ajouter des crédits de test"""
    balance = db.query(CreditBalance).filter(
        CreditBalance.tenant_id == current["tenant_id"]
    ).first()
    balance.balance += 10
    db.commit()
    return {"message": "10 crédits ajoutés", "balance": balance.balance}


@router.get("/credits/balance")
def get_balance(
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_tenant)
):
    balance = db.query(CreditBalance).filter(
        CreditBalance.tenant_id == current["tenant_id"]
    ).first()
    return {"balance": balance.balance if balance else 0}