from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.credit import CreditBalance, CreditTransaction
from app.models.tenant import Tenant
from app.dependencies import get_current_tenant, require_admin, require_superadmin
from app.schemas.credit import CreditAddRequest, CreditDeductRequest

router = APIRouter(prefix="/credits", tags=["Crédits"])


@router.get("/balance")
def get_balance(
    db: Session = Depends(get_db),
    current: dict = Depends(require_admin),
):
    balance = db.query(CreditBalance).filter(
        CreditBalance.tenant_id == current["tenant_id"]
    ).first()
    return {"balance": balance.balance if balance else 0, "tenant_id": current["tenant_id"]}


@router.post("/add")
def add_credits(
    payload: CreditAddRequest,
    db: Session = Depends(get_db),
    current: dict = Depends(require_superadmin),
):
    balance = db.query(CreditBalance).filter(
        CreditBalance.tenant_id == str(payload.tenant_id)
    ).first()
    if not balance:
        balance = CreditBalance(tenant_id=str(payload.tenant_id), balance=0)
        db.add(balance)

    balance.balance += payload.amount

    tx = CreditTransaction(
        tenant_id=str(payload.tenant_id),
        amount=payload.amount,
        description=payload.description or f"Ajout de {payload.amount} crédit(s)",
    )
    db.add(tx)
    db.commit()
    db.refresh(balance)
    return {"message": f"{payload.amount} crédit(s) ajouté(s)", "balance": balance.balance}


@router.post("/deduct")
def deduct_credits(
    payload: CreditDeductRequest,
    db: Session = Depends(get_db),
    current: dict = Depends(require_superadmin),
):
    balance = db.query(CreditBalance).filter(
        CreditBalance.tenant_id == str(payload.tenant_id)
    ).first()
    if not balance or balance.balance < payload.amount:
        raise HTTPException(status_code=400, detail="Solde insuffisant pour cette déduction")

    balance.balance -= payload.amount

    tx = CreditTransaction(
        tenant_id=str(payload.tenant_id),
        amount=-payload.amount,
        description=payload.description or f"Déduction de {payload.amount} crédit(s)",
    )
    db.add(tx)
    db.commit()
    db.refresh(balance)
    return {"message": f"{payload.amount} crédit(s) déduit(s)", "balance": balance.balance}


@router.get("/history")
def get_history(
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
    current: dict = Depends(require_admin),
):
    offset = (page - 1) * limit
    total = db.query(func.count(CreditTransaction.id)).filter(
        CreditTransaction.tenant_id == current["tenant_id"]
    ).scalar()

    transactions = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.tenant_id == current["tenant_id"])
        .order_by(CreditTransaction.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "pages": max(1, (total + limit - 1) // limit),
        "items": [
            {
                "id": str(t.id),
                "tenant_id": str(t.tenant_id),
                "amount": t.amount,
                "description": t.description,
                "created_at": t.created_at,
            }
            for t in transactions
        ],
    }


@router.get("/all-balances")
def get_all_balances(
    db: Session = Depends(get_db),
    current: dict = Depends(require_superadmin),
):
    results = (
        db.query(
            Tenant.id,
            Tenant.name,
            Tenant.slug,
            Tenant.is_active,
            func.coalesce(CreditBalance.balance, 0).label("balance"),
        )
        .outerjoin(CreditBalance, CreditBalance.tenant_id == Tenant.id)
        .all()
    )
    return [
        {
            "tenant_id": str(r.id),
            "tenant_name": r.name,
            "tenant_slug": r.slug,
            "is_active": r.is_active,
            "balance": r.balance,
        }
        for r in results
    ]
