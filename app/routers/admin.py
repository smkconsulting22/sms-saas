import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.models.campaign import Campaign, CampaignLog
from app.models.credit import CreditBalance, CreditTransaction
from app.models.recharge_request import RechargeRequest
from app.models.account_request import AccountRequest
from app.dependencies import require_superadmin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/dashboard")
def admin_dashboard(
    db: Session = Depends(get_db),
    current: dict = Depends(require_superadmin),
):
    """Tableau de bord super admin : métriques globales de la plateforme."""
    total_tenants = db.query(func.count(Tenant.id)).scalar() or 0
    active_tenants = db.query(func.count(Tenant.id)).filter(Tenant.is_active == True).scalar() or 0

    total_credits_distributed = db.query(
        func.coalesce(func.sum(CreditTransaction.amount), 0)
    ).filter(CreditTransaction.amount > 0).scalar() or 0

    total_sms_sent = db.query(func.coalesce(func.sum(Campaign.sent), 0)).scalar() or 0
    total_campaigns = db.query(func.count(Campaign.id)).scalar() or 0

    pending_recharge = db.query(func.count(RechargeRequest.id)).filter(
        RechargeRequest.status == "pending"
    ).scalar() or 0

    pending_accounts = db.query(func.count(AccountRequest.id)).filter(
        AccountRequest.status == "pending"
    ).scalar() or 0

    # Top 10 tenants par SMS envoyés
    top_rows = (
        db.query(
            Tenant.id,
            Tenant.name,
            func.coalesce(func.sum(Campaign.sent), 0).label("sms_sent"),
            func.coalesce(func.max(Campaign.created_at), None).label("last_activity"),
            func.count(Campaign.id).label("campaigns_count"),
        )
        .outerjoin(Campaign, Campaign.tenant_id == Tenant.id)
        .group_by(Tenant.id, Tenant.name)
        .order_by(func.coalesce(func.sum(Campaign.sent), 0).desc())
        .limit(10)
        .all()
    )

    balances = {
        str(b.tenant_id): b.balance
        for b in db.query(CreditBalance).all()
    }

    top_tenants = [
        {
            "tenant_id": str(row.id),
            "tenant_name": row.name,
            "sms_sent": row.sms_sent,
            "credits_balance": balances.get(str(row.id), 0),
            "campaigns_count": row.campaigns_count,
            "last_activity": row.last_activity,
        }
        for row in top_rows
    ]

    # SMS par jour (30 derniers jours) — via CampaignLog
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    sms_per_day_rows = (
        db.query(
            func.date(CampaignLog.created_at).label("date"),
            func.count(CampaignLog.id).label("count"),
        )
        .filter(CampaignLog.created_at >= thirty_days_ago, CampaignLog.status == "sent")
        .group_by(func.date(CampaignLog.created_at))
        .order_by(func.date(CampaignLog.created_at))
        .all()
    )
    sms_per_day = [{"date": str(r.date), "count": r.count} for r in sms_per_day_rows]

    # Crédits distribués par jour (30 derniers jours)
    credits_per_day_rows = (
        db.query(
            func.date(CreditTransaction.created_at).label("date"),
            func.sum(CreditTransaction.amount).label("amount"),
        )
        .filter(
            CreditTransaction.created_at >= thirty_days_ago,
            CreditTransaction.amount > 0,
        )
        .group_by(func.date(CreditTransaction.created_at))
        .order_by(func.date(CreditTransaction.created_at))
        .all()
    )
    credits_per_day = [{"date": str(r.date), "amount": int(r.amount)} for r in credits_per_day_rows]

    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "total_credits_distributed": int(total_credits_distributed),
        "total_sms_sent": int(total_sms_sent),
        "total_campaigns": total_campaigns,
        "pending_recharge_requests": pending_recharge,
        "pending_account_requests": pending_accounts,
        "top_tenants": top_tenants,
        "sms_per_day": sms_per_day,
        "credits_per_day": credits_per_day,
    }


@router.get("/tenants/{tenant_id}/consumption")
def tenant_consumption(
    tenant_id: str,
    db: Session = Depends(get_db),
    current: dict = Depends(require_superadmin),
):
    """Consommation détaillée d'un tenant (super admin)."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Tenant introuvable")

    balance_row = db.query(CreditBalance).filter(
        CreditBalance.tenant_id == tenant_id
    ).first()
    credits_balance = balance_row.balance if balance_row else 0

    total_credits_purchased = db.query(
        func.coalesce(func.sum(CreditTransaction.amount), 0)
    ).filter(
        CreditTransaction.tenant_id == tenant_id,
        CreditTransaction.amount > 0,
    ).scalar() or 0

    total_sms_sent = db.query(
        func.coalesce(func.sum(Campaign.sent), 0)
    ).filter(Campaign.tenant_id == tenant_id).scalar() or 0

    total_sms_failed = db.query(
        func.coalesce(func.sum(Campaign.failed), 0)
    ).filter(Campaign.tenant_id == tenant_id).scalar() or 0

    campaigns = db.query(Campaign).filter(
        Campaign.tenant_id == tenant_id
    ).order_by(Campaign.created_at.desc()).limit(50).all()

    credit_transactions = db.query(CreditTransaction).filter(
        CreditTransaction.tenant_id == tenant_id
    ).order_by(CreditTransaction.created_at.desc()).limit(50).all()

    # SMS par jour (30 derniers jours)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    sms_per_day_rows = (
        db.query(
            func.date(CampaignLog.created_at).label("date"),
            func.count(CampaignLog.id).label("count"),
        )
        .join(Campaign, Campaign.id == CampaignLog.campaign_id)
        .filter(
            Campaign.tenant_id == tenant_id,
            CampaignLog.created_at >= thirty_days_ago,
            CampaignLog.status == "sent",
        )
        .group_by(func.date(CampaignLog.created_at))
        .order_by(func.date(CampaignLog.created_at))
        .all()
    )
    sms_per_day = [{"date": str(r.date), "count": r.count} for r in sms_per_day_rows]

    return {
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name,
        "credits_balance": credits_balance,
        "total_credits_purchased": int(total_credits_purchased),
        "total_sms_sent": int(total_sms_sent),
        "total_sms_failed": int(total_sms_failed),
        "campaigns": [
            {
                "id": str(c.id),
                "name": c.name,
                "status": c.status,
                "total": c.total,
                "sent": c.sent,
                "failed": c.failed,
                "scheduled_at": c.scheduled_at,
                "created_at": c.created_at,
            }
            for c in campaigns
        ],
        "credit_transactions": [
            {
                "id": str(t.id),
                "amount": t.amount,
                "description": t.description,
                "created_at": t.created_at,
            }
            for t in credit_transactions
        ],
        "sms_per_day": sms_per_day,
    }
