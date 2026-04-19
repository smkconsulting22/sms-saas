import logging
import re
import secrets
import string
import traceback
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.account_request import AccountRequest
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.models.credit import CreditBalance
from app.dependencies import require_superadmin
from app.schemas.account_request import AccountRequestCreate, AccountRejectRequest
from app.services.auth import hash_password
from app.services.email import (
    send_account_request_confirmation,
    send_account_request_superadmin,
    send_account_approved_email,
    send_account_rejected_email,
)
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/account-requests", tags=["Demandes de compte"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_temp_password(length: int = 12) -> str:
    """Génère un mot de passe temporaire sécurisé."""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _generate_unique_slug(db: Session, company_name: str) -> str:
    """Génère un slug unique depuis le nom d'entreprise, avec suffixe si conflit."""
    base = re.sub(r"[^a-z0-9]+", "-", company_name.lower().strip()).strip("-")[:40]
    slug = base or "entreprise"
    counter = 1
    while db.query(Tenant).filter(Tenant.slug == slug).first():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def _request_to_dict(req: AccountRequest) -> dict:
    return {
        "id": str(req.id),
        "full_name": req.full_name,
        "company_name": req.company_name,
        "email": req.email,
        "phone": req.phone,
        "message": req.message,
        "status": req.status,
        "rejection_reason": req.rejection_reason,
        "created_at": req.created_at,
        "updated_at": req.updated_at,
    }


# ── Endpoint public ───────────────────────────────────────────────────────────

@router.post("/", status_code=201)
def submit_account_request(
    payload: AccountRequestCreate,
    db: Session = Depends(get_db),
):
    """Soumet une demande de création de compte (public, sans authentification)."""

    # L'email ne doit pas déjà exister dans la table users
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=409,
            detail="Un compte existe déjà avec cet email.",
        )

    # Éviter les doublons de demandes en attente ou déjà approuvées
    existing = (
        db.query(AccountRequest)
        .filter(
            AccountRequest.email == payload.email,
            AccountRequest.status.in_(["pending", "approved"]),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Une demande est déjà en cours ou a déjà été approuvée pour cet email.",
        )

    try:
        req = AccountRequest(
            full_name=payload.full_name,
            company_name=payload.company_name,
            email=payload.email,
            phone=payload.phone,
            message=payload.message,
            status="pending",
        )
        db.add(req)
        db.commit()
        db.refresh(req)
    except Exception:
        db.rollback()
        tb = traceback.format_exc()
        print(f"[ACCOUNT_REQUEST] ERREUR db.commit : {tb}")
        logger.error("Erreur création demande de compte email=%s :\n%s", payload.email, tb)
        raise HTTPException(status_code=500, detail="Erreur lors de la soumission de la demande")

    logger.info(
        "Demande de compte soumise id=%s email=%s company=%s",
        req.id, req.email, req.company_name,
    )
    print(f"[ACCOUNT_REQUEST] Demande créée id={req.id} email={req.email}")

    # Emails — non bloquants
    try:
        send_account_request_confirmation(req.email, req.full_name, req.company_name)
    except Exception:
        print(f"[ACCOUNT_REQUEST] Email confirmation échoué : {traceback.format_exc()}")
    try:
        dashboard_url = f"{settings.FRONTEND_URL}/admin/account-requests"
        send_account_request_superadmin(
            to=settings.SMTP_USER,
            full_name=req.full_name,
            company_name=req.company_name,
            email=req.email,
            phone=req.phone or "—",
            message=req.message,
            dashboard_url=dashboard_url,
        )
    except Exception:
        print(f"[ACCOUNT_REQUEST] Email superadmin échoué : {traceback.format_exc()}")

    return {
        "message": (
            "Votre demande a bien été soumise. "
            "Vous recevrez un email de confirmation dès qu'elle sera traitée."
        )
    }


# ── Endpoints super admin ─────────────────────────────────────────────────────

@router.get("/")
def list_account_requests(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current: dict = Depends(require_superadmin),
):
    """Liste toutes les demandes de compte. Filtre optionnel : ?status=pending."""
    offset = (page - 1) * limit

    q = db.query(AccountRequest)
    if status:
        q = q.filter(AccountRequest.status == status)

    total = q.with_entities(func.count(AccountRequest.id)).scalar()
    requests = q.order_by(AccountRequest.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "pages": max(1, (total + limit - 1) // limit),
        "items": [_request_to_dict(r) for r in requests],
    }


@router.patch("/{request_id}/approve")
def approve_account_request(
    request_id: str,
    db: Session = Depends(get_db),
    current: dict = Depends(require_superadmin),
):
    """Approuve une demande : crée le tenant, l'utilisateur admin et envoie les identifiants."""
    req = db.query(AccountRequest).filter(AccountRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if req.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Impossible d'approuver une demande au statut '{req.status}'",
        )

    # Vérifier une dernière fois que l'email n'a pas été pris entre-temps
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(
            status_code=409,
            detail="Un compte existe déjà avec cet email. La demande ne peut pas être approuvée.",
        )

    # Générer les identifiants
    temp_password = _generate_temp_password()
    slug = _generate_unique_slug(db, req.company_name)

    # Créer le tenant
    tenant = Tenant(name=req.company_name, slug=slug)
    db.add(tenant)
    db.flush()

    # Créer l'utilisateur admin
    user = User(
        tenant_id=tenant.id,
        email=req.email,
        hashed_password=hash_password(temp_password),
        full_name=req.full_name,
        role=UserRole.ADMIN,
    )
    db.add(user)

    # Créer le solde de crédits à 0
    balance = CreditBalance(tenant_id=tenant.id, balance=0)
    db.add(balance)

    # Mettre à jour la demande
    req.status = "approved"
    db.commit()

    logger.info(
        "Compte approuvé request_id=%s email=%s tenant=%s slug=%s",
        request_id, req.email, tenant.id, slug,
    )

    # Email avec identifiants — non bloquant
    try:
        send_account_approved_email(
            to=req.email,
            full_name=req.full_name,
            company_name=req.company_name,
            temp_password=temp_password,
            login_url=f"{settings.FRONTEND_URL}/login",
        )
    except Exception:
        pass

    return _request_to_dict(req)


@router.patch("/{request_id}/reject")
def reject_account_request(
    request_id: str,
    payload: AccountRejectRequest,
    db: Session = Depends(get_db),
    current: dict = Depends(require_superadmin),
):
    """Rejette une demande et notifie le demandeur avec la raison."""
    req = db.query(AccountRequest).filter(AccountRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if req.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de rejeter une demande au statut '{req.status}'",
        )

    req.status = "rejected"
    req.rejection_reason = payload.reason
    db.commit()
    db.refresh(req)
    logger.info(
        "Demande rejetée request_id=%s email=%s reason=%s",
        request_id, req.email, payload.reason[:50],
    )

    # Email au demandeur — non bloquant
    try:
        send_account_rejected_email(req.email, req.full_name, payload.reason)
    except Exception:
        pass

    return _request_to_dict(req)
