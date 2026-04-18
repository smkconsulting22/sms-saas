import logging
import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from app.database import get_db
from app.models.recharge_request import RechargeRequest
from app.models.credit import CreditBalance, CreditTransaction
from app.models.tenant import Tenant
from app.models.user import User
from app.dependencies import require_admin, require_superadmin
from app.schemas.recharge import (
    RechargeRequestCreate,
    RechargeApproveRequest,
    RechargeRejectRequest,
)
from app.services.email import (
    send_recharge_notification_superadmin,
    send_recharge_approved_email,
    send_recharge_rejected_email,
)
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recharge", tags=["Rechargements"])


def _recharge_to_dict(req: RechargeRequest, tenant_name: Optional[str] = None) -> dict:
    return {
        "id": str(req.id),
        "tenant_id": str(req.tenant_id),
        "tenant_name": tenant_name,
        "amount_requested": req.amount_requested,
        "amount_paid": str(req.amount_paid),
        "payment_method": req.payment_method,
        "payment_reference": req.payment_reference,
        "status": req.status,
        "note": req.note,
        "created_at": req.created_at,
        "updated_at": req.updated_at,
    }


# ── CLIENT ────────────────────────────────────────────────────────────────────

@router.post("/request", status_code=201)
def create_recharge_request(
    payload: RechargeRequestCreate,
    db: Session = Depends(get_db),
    current: dict = Depends(require_admin),
):
    """Soumet une demande de rechargement (client admin)."""
    tenant_id = current["tenant_id"]

    try:
        # Calculer amount_paid depuis sms_price du tenant si non fourni
        tenant_for_price = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        sms_price = float(tenant_for_price.sms_price) if (tenant_for_price and tenant_for_price.sms_price) else 20.0
        computed_amount_paid = (
            payload.amount_paid
            if payload.amount_paid is not None
            else round(payload.amount_requested * sms_price, 2)
        )

        req = RechargeRequest(
            tenant_id=tenant_id,
            amount_requested=payload.amount_requested,
            amount_paid=computed_amount_paid,
            payment_method=payload.payment_method,
            payment_reference=payload.payment_reference,
            status="pending",
            note=payload.note,
        )
        db.add(req)
        db.commit()
        db.refresh(req)
    except Exception:
        db.rollback()
        logger.error(
            "Erreur création demande rechargement tenant=%s :\n%s",
            tenant_id, traceback.format_exc(),
        )
        raise HTTPException(status_code=500, detail="Erreur lors de la création de la demande")

    logger.info(
        "Demande rechargement créée id=%s tenant=%s amount=%d method=%s",
        req.id, tenant_id, payload.amount_requested, payload.payment_method,
    )

    # Notifier le super admin — non bloquant
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        tenant_name = tenant.name if tenant else str(tenant_id)
        dashboard_url = f"{settings.FRONTEND_URL}/admin/recharge"
        send_recharge_notification_superadmin(
            to=settings.SMTP_USER,
            tenant_name=tenant_name,
            amount_requested=payload.amount_requested,
            amount_paid=str(payload.amount_paid) if payload.amount_paid is not None else "N/A",
            payment_method=payload.payment_method,
            payment_reference=payload.payment_reference,
            dashboard_url=dashboard_url,
        )
    except Exception:
        logger.warning("Notification super admin échouée :\n%s", traceback.format_exc())

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    return _recharge_to_dict(req, tenant.name if tenant else None)


@router.get("/my-requests")
def get_my_requests(
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
    current: dict = Depends(require_admin),
):
    """Liste les demandes du tenant connecté."""
    tenant_id = current["tenant_id"]
    offset = (page - 1) * limit

    total = db.query(func.count(RechargeRequest.id)).filter(
        RechargeRequest.tenant_id == tenant_id
    ).scalar()

    requests = (
        db.query(RechargeRequest)
        .filter(RechargeRequest.tenant_id == tenant_id)
        .order_by(RechargeRequest.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    tenant_name = tenant.name if tenant else None

    return {
        "total": total,
        "page": page,
        "pages": max(1, (total + limit - 1) // limit),
        "items": [_recharge_to_dict(r, tenant_name) for r in requests],
    }


# ── SUPER ADMIN ───────────────────────────────────────────────────────────────

@router.get("/all")
def get_all_requests(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current: dict = Depends(require_superadmin),
):
    """Liste toutes les demandes (super admin). Filtre optionnel : ?status=pending."""
    offset = (page - 1) * limit

    q = db.query(RechargeRequest)
    if status:
        q = q.filter(RechargeRequest.status == status)

    total = q.with_entities(func.count(RechargeRequest.id)).scalar()
    requests = q.order_by(RechargeRequest.created_at.desc()).offset(offset).limit(limit).all()

    # Charger les noms de tenants en une requête
    tenant_ids = list({r.tenant_id for r in requests})
    tenants = {
        str(t.id): t.name
        for t in db.query(Tenant).filter(Tenant.id.in_(tenant_ids)).all()
    }

    return {
        "total": total,
        "page": page,
        "pages": max(1, (total + limit - 1) // limit),
        "items": [_recharge_to_dict(r, tenants.get(str(r.tenant_id))) for r in requests],
    }


@router.patch("/{request_id}/approve")
def approve_request(
    request_id: str,
    payload: RechargeApproveRequest,
    db: Session = Depends(get_db),
    current: dict = Depends(require_superadmin),
):
    """Approuve une demande, crédite le tenant et notifie le client."""
    req = db.query(RechargeRequest).filter(RechargeRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if req.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Impossible d'approuver une demande au statut '{req.status}'"
        )

    # Recalculer amount_paid depuis sms_price du tenant
    tenant_for_price = db.query(Tenant).filter(Tenant.id == str(req.tenant_id)).first()
    sms_price = float(tenant_for_price.sms_price) if (tenant_for_price and tenant_for_price.sms_price) else 20.0
    req.amount_paid = round(req.amount_requested * sms_price, 2)

    # Créditer le tenant
    balance = db.query(CreditBalance).filter(
        CreditBalance.tenant_id == str(req.tenant_id)
    ).first()
    if not balance:
        balance = CreditBalance(tenant_id=str(req.tenant_id), balance=0)
        db.add(balance)

    balance.balance += req.amount_requested

    tx = CreditTransaction(
        tenant_id=str(req.tenant_id),
        amount=req.amount_requested,
        description=f"Rechargement approuvé — réf. {req.payment_reference}",
    )
    db.add(tx)

    # Mettre à jour la demande
    req.status = "approved"
    req.note = payload.note

    db.commit()
    db.refresh(balance)
    db.refresh(req)
    logger.info(
        "Rechargement approuvé id=%s tenant=%s amount=%d new_balance=%d",
        request_id, req.tenant_id, req.amount_requested, balance.balance,
    )

    # Notifier le client — non bloquant
    try:
        tenant = db.query(Tenant).filter(Tenant.id == str(req.tenant_id)).first()
        admin = db.query(User).filter(
            User.tenant_id == str(req.tenant_id),
            User.role == "admin",
            User.is_active == True,
        ).first()
        if tenant and admin:
            send_recharge_approved_email(
                to=admin.email,
                tenant_name=tenant.name,
                amount_requested=req.amount_requested,
                new_balance=balance.balance,
                note=payload.note,
            )
    except Exception:
        pass

    tenant = db.query(Tenant).filter(Tenant.id == str(req.tenant_id)).first()
    return _recharge_to_dict(req, tenant.name if tenant else None)


@router.patch("/{request_id}/reject")
def reject_request(
    request_id: str,
    payload: RechargeRejectRequest,
    db: Session = Depends(get_db),
    current: dict = Depends(require_superadmin),
):
    """Rejette une demande et notifie le client avec la raison."""
    req = db.query(RechargeRequest).filter(RechargeRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if req.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de rejeter une demande au statut '{req.status}'"
        )

    req.status = "rejected"
    req.note = payload.reason
    db.commit()
    db.refresh(req)
    logger.info(
        "Rechargement rejeté id=%s tenant=%s reason=%s",
        request_id, req.tenant_id, payload.reason[:50],
    )

    # Notifier le client — non bloquant
    try:
        tenant = db.query(Tenant).filter(Tenant.id == str(req.tenant_id)).first()
        admin = db.query(User).filter(
            User.tenant_id == str(req.tenant_id),
            User.role == "admin",
            User.is_active == True,
        ).first()
        if tenant and admin:
            send_recharge_rejected_email(
                to=admin.email,
                tenant_name=tenant.name,
                amount_requested=req.amount_requested,
                reason=payload.reason,
            )
    except Exception:
        pass

    tenant = db.query(Tenant).filter(Tenant.id == str(req.tenant_id)).first()
    return _recharge_to_dict(req, tenant.name if tenant else None)
