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
from app.routers.credits import require_admin
from app.schemas.tenant import TenantUpdate

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.get("/")
def list_tenants(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current: dict = Depends(require_admin),
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
        items.append(
            {
                "id": str(t.id),
                "name": t.name,
                "slug": t.slug,
                "is_active": t.is_active,
                "created_at": t.created_at,
                "credits_balance": balance.balance if balance else 0,
                "contacts_count": contacts_count,
                "campaigns_count": campaigns_count,
            }
        )

    return {"total": total, "page": page, "pages": max(1, (total + limit - 1) // limit), "items": items}


@router.get("/{tenant_id}")
def get_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current: dict = Depends(require_admin),
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
    current: dict = Depends(require_admin),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant introuvable")

    if payload.name is not None:
        tenant.name = payload.name
    if payload.is_active is not None:
        tenant.is_active = payload.is_active

    db.commit()
    db.refresh(tenant)
    return {"message": "Tenant mis à jour", "id": str(tenant.id), "name": tenant.name, "is_active": tenant.is_active}


@router.get("/{tenant_id}/users")
def get_tenant_users(
    tenant_id: str,
    db: Session = Depends(get_db),
    current: dict = Depends(require_admin),
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
    current: dict = Depends(require_admin),
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
