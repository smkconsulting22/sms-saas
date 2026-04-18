from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from typing import Optional

VALID_PAYMENT_METHODS = {"orange_money", "wave"}


class RechargeRequestCreate(BaseModel):
    amount_requested: int = Field(gt=0, description="Nombre de crédits demandés")
    amount_paid: Optional[Decimal] = Field(default=None, description="Montant payé en FCFA (optionnel)")
    payment_method: str = Field(description="'orange_money' ou 'wave'")
    payment_reference: str = Field(min_length=3, description="Référence de la transaction")
    note: Optional[str] = Field(default=None, max_length=255)

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        if v not in VALID_PAYMENT_METHODS:
            raise ValueError(
                f"Méthode invalide. Valeurs acceptées : {', '.join(sorted(VALID_PAYMENT_METHODS))}"
            )
        return v


class RechargeRequestOut(BaseModel):
    id: UUID
    tenant_id: UUID
    tenant_name: Optional[str] = None
    amount_requested: int
    amount_paid: Decimal
    payment_method: str
    payment_reference: str
    status: str
    note: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RechargeApproveRequest(BaseModel):
    note: Optional[str] = Field(default=None, max_length=255)


class RechargeRejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=255)
