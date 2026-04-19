import logging
from datetime import datetime, timezone
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
from app.schemas.tenant import TenantUpdate, SenderNameUpdate, SenderNameRequest, SenderNameStatusUpdate
from app.config import settings

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
        "sender_name_requested": tenant.sender_name_requested,
        "sender_name_status": tenant.sender_name_status,
        "sender_name_requested_at": tenant.sender_name_requested_at,
        "sender_name_approved_at": tenant.sender_name_approved_at,
        "sender_name_rejection_reason": tenant.sender_name_rejection_reason,
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


@router.post("/me/sender-name-request", status_code=201)
def request_sender_name(
    payload: SenderNameRequest,
    db: Session = Depends(get_db),
    current: dict = Depends(require_admin),
):
    """Soumet une demande d'approbation de sender name personnalisé."""
    from app.services.email import send_sender_name_request_superadmin

    tenant_id = current["tenant_id"]
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant introuvable")

    if tenant.sender_name_status == "pending":
        raise HTTPException(status_code=409, detail="Une demande est déjà en cours de traitement")

    tenant.sender_name_requested = payload.sender_name
    tenant.sender_name_status = "pending"
    tenant.sender_name_requested_at = datetime.now(timezone.utc)
    tenant.sender_name_approved_at = None
    tenant.sender_name_rejection_reason = None
    db.commit()

    superadmins = db.query(User).filter(User.role == "superadmin", User.is_active == True).all()
    dashboard_url = f"{settings.FRONTEND_URL}/admin/tenants/{tenant_id}"
    for sa in superadmins:
        send_sender_name_request_superadmin(
            to=sa.email,
            tenant_name=tenant.name,
            sender_name_requested=payload.sender_name,
            dashboard_url=dashboard_url,
        )

    logger.info("Sender name request tenant=%s requested=%s", tenant_id, payload.sender_name)
    return {
        "message": "Demande soumise — en attente d'approbation",
        "sender_name_requested": tenant.sender_name_requested,
        "sender_name_status": tenant.sender_name_status,
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


@router.patch("/{tenant_id}/sender-name")
def review_sender_name(
    tenant_id: str,
    payload: SenderNameStatusUpdate,
    db: Session = Depends(get_db),
    current: dict = Depends(require_superadmin),
):
    """Approuve ou refuse une demande de sender name (super admin uniquement)."""
    from app.services.email import send_sender_name_approved_email, send_sender_name_rejected_email

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant introuvable")
    if tenant.sender_name_status != "pending":
        raise HTTPException(status_code=409, detail="Aucune demande en attente pour ce tenant")

    tenant_admin = (
        db.query(User)
        .filter(User.tenant_id == tenant_id, User.role == "admin", User.is_active == True)
        .first()
    )

    if payload.status == "approved":
        tenant.sender_name = tenant.sender_name_requested
        tenant.sender_name_status = "approved"
        tenant.sender_name_approved_at = datetime.now(timezone.utc)
        tenant.sender_name_rejection_reason = None
        db.commit()
        logger.info(
            "Sender name approuvé tenant=%s sender_name=%s par superadmin=%s",
            tenant_id, tenant.sender_name, current.get("user_id"),
        )
        if tenant_admin:
            send_sender_name_approved_email(
                to=tenant_admin.email,
                tenant_name=tenant.name,
                sender_name=tenant.sender_name,
            )
        return {
            "message": "Sender name approuvé",
            "sender_name": tenant.sender_name,
            "sender_name_status": tenant.sender_name_status,
        }
    else:
        if not payload.rejection_reason:
            raise HTTPException(status_code=422, detail="rejection_reason requis en cas de refus")
        tenant.sender_name_status = "rejected"
        tenant.sender_name_rejection_reason = payload.rejection_reason
        tenant.sender_name_approved_at = None
        db.commit()
        logger.info(
            "Sender name refusé tenant=%s reason=%s par superadmin=%s",
            tenant_id, payload.rejection_reason, current.get("user_id"),
        )
        if tenant_admin:
            send_sender_name_rejected_email(
                to=tenant_admin.email,
                tenant_name=tenant.name,
                sender_name=tenant.sender_name_requested,
                reason=payload.rejection_reason,
            )
        return {
            "message": "Sender name refusé",
            "sender_name_status": tenant.sender_name_status,
            "rejection_reason": tenant.sender_name_rejection_reason,
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
