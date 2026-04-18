import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.models.credit import CreditBalance
from app.models.contact import Contact
from app.models.campaign import Campaign
from app.dependencies import require_admin, require_superadmin
from app.schemas.tenant import TenantUpdate, SenderNameUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tenants", tags=["Tenants"])


# ── Endpoints client (require_admin) ─────────────────────────────────────────
# IMPORTANT : déclarés avant /{tenant_id} pour éviter que "me" soit capturé
# comme un paramètre de chemin.

@router.get("/me")
def get_my_tenant(
    db: Session = Depends(get_db),
    current: dict = Depends(require_admin),
):
    """Retourne les informations du tenant de l'utilisateur connecté."""
    tenant_id = current["tenant_id"]
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant introuvable")

    balance = db.query(CreditBalance).filter(CreditBalance.tenant_id == tenant_id).first()
    contacts_count = (
        db.query(func.count(Contact.id)).filter(Contact.tenant_id == tenant_id).scalar() or 0
    )
    campaigns_count = (
        db.query(func.count(Campaign.id)).filter(Campaign.tenant_id == tenant_id).scalar() or 0
    )

    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "slug": tenant.slug,
        "is_active": tenant.is_active,
        "sender_name": tenant.sender_name,
        "sms_price": float(tenant.sms_price) if tenant.sms_price is not None else 20.0,
        "created_at": tenant.created_at,
        "credits_balance": balance.balance if balance else 0,
        "contacts_count": contacts_count,
        "campaigns_count": campaigns_count,
    }


@router.get("/me/pricing")
def get_my_pricing(
    db: Session = Depends(get_db),
    current: dict = Depends(require_admin),
):
    """Retourne le prix SMS appliqué au tenant connecté."""
    tenant_id = current["tenant_id"]
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant introuvable")
    sms_price = float(tenant.sms_price) if tenant.sms_price is not None else 20.0
    return {
        "sms_price": sms_price,
        "currency": "FCFA",
        "description": f"1 crédit SMS = {sms_price} FCFA",
    }


@router.patch("/me/sender-name")
def update_my_sender_name(
    payload: SenderNameUpdate,
    db: Session = Depends(get_db),
    current: dict = Depends(require_admin),
):
    """Permet au client admin de définir son propre sender name (1-11 car. alphanumériques)."""
    tenant_id = current["tenant_id"]
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant introuvable")

    tenant.sender_name = payload.sender_name
    db.commit()
    db.refresh(tenant)
    logger.info("Sender name mis à jour tenant=%s sender_name=%s", tenant_id, payload.sender_name)
    return {
        "message": "Sender name mis à jour",
        "sender_name": tenant.sender_name,
    }


# ── Endpoints super admin (require_superadmin) ────────────────────────────────

@router.get("/")
def list_tenants(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current: dict = Depends(require_superadmin),
):
    q = db.query(Tenant)
    if search:
        q = q.filter(
            Tenant.name.ilike(f"%{search}%") | Tenant.slug.ilike(f"%{search}%")
        )

    total = q.count()
    tenants = q.order_by(Tenant.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    items = []
    for t in tenants:
        balance = db.query(CreditBalance).filter(CreditBalance.tenant_id == t.id).first()
        contacts_count = (
            db.query(func.count(Contact.id)).filter(Contact.tenant_id == t.id).scalar() or 0
        )
        campaigns_count = (
            db.query(func.count(Campaign.id)).filter(Campaign.tenant_id == t.id).scalar() or 0
        )
        items.append({
            "id": str(t.id),
            "name": t.name,
            "slug": t.slug,
            "is_active": t.is_active,
            "sender_name": t.sender_name,
            "sms_price": float(t.sms_price) if t.sms_price is not None else 20.0,
            "created_at": t.created_at,
            "credits_balance": balance.balance if balance else 0,
            "contacts_count": contacts_count,
            "campaigns_count": campaigns_count,
        })

    return {"total": total, "page": page, "pages": max(1, (total + limit - 1) // limit), "items": items}


@router.get("/{tenant_id}")
def get_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current: dict = Depends(require_superadmin),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant introuvable")

    balance = db.query(CreditBalance).filter(CreditBalance.tenant_id == tenant_id).first()
    contacts_count = (
        db.query(func.count(Contact.id)).filter(Contact.tenant_id == tenant_id).scalar() or 0
    )
    campaigns_count = (
        db.query(func.count(Campaign.id)).filter(Campaign.tenant_id == tenant_id).scalar() or 0
    )
    sms_sent = (
        db.query(func.sum(Campaign.sent)).filter(Campaign.tenant_id == tenant_id).scalar() or 0
    )
    users = db.query(User).filter(User.tenant_id == tenant_id).all()

    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "slug": tenant.slug,
        "is_active": tenant.is_active,
        "sender_name": tenant.sender_name,
        "sms_price": float(tenant.sms_price) if tenant.sms_price is not None else 20.0,
        "created_at": tenant.created_at,
        "credits_balance": balance.balance if balance else 0,
        "contacts_count": contacts_count,
        "campaigns_count": campaigns_count,
        "sms_sent": sms_sent,
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at,
            }
            for u in users
        ],
    }


@router.patch("/{tenant_id}")
def update_tenant(
    tenant_id: str,
    payload: TenantUpdate,
    db: Session = Depends(get_db),
    current: dict = Depends(require_superadmin),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant introuvable")

    if payload.name is not None:
        tenant.name = payload.name
    if payload.is_active is not None:
        tenant.is_active = payload.is_active
    if payload.sms_price is not None:
        tenant.sms_price = payload.sms_price
        logger.info(
            "sms_price mis à jour tenant=%s price=%s par super_admin=%s",
            tenant_id, payload.sms_price, current.get("user_id"),
        )

    db.commit()
    db.refresh(tenant)
    return {
        "message": "Tenant mis à jour",
        "id": str(tenant.id),
        "name": tenant.name,
        "is_active": tenant.is_active,
        "sender_name": tenant.sender_name,
        "sms_price": float(tenant.sms_price) if tenant.sms_price is not None else 20.0,
    }


@router.get("/{tenant_id}/users")
def get_tenant_users(
    tenant_id: str,
    db: Session = Depends(get_db),
    current: dict = Depends(require_superadmin),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant introuvable")

    users = db.query(User).filter(User.tenant_id == tenant_id).all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.get("/{tenant_id}/stats")
def get_tenant_stats(
    tenant_id: str,
    db: Session = Depends(get_db),
    current: dict = Depends(require_superadmin),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant introuvable")

    balance = db.query(CreditBalance).filter(CreditBalance.tenant_id == tenant_id).first()
    contacts_count = (
        db.query(func.count(Contact.id)).filter(Contact.tenant_id == tenant_id).scalar() or 0
    )
    campaigns_count = (
        db.query(func.count(Campaign.id)).filter(Campaign.tenant_id == tenant_id).scalar() or 0
    )
    sms_sent = (
        db.query(func.sum(Campaign.sent)).filter(Campaign.tenant_id == tenant_id).scalar() or 0
    )

    return {
        "tenant_id": tenant_id,
        "contacts_count": contacts_count,
        "campaigns_count": campaigns_count,
        "sms_sent": sms_sent,
        "credits_balance": balance.balance if balance else 0,
    }
