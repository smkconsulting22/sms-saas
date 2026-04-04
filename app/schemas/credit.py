from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class CreditAddRequest(BaseModel):
    tenant_id: UUID
    amount: int = Field(gt=0, description="Nombre de crédits à ajouter")
    description: Optional[str] = None


class CreditDeductRequest(BaseModel):
    tenant_id: UUID
    amount: int = Field(gt=0, description="Nombre de crédits à déduire")
    description: Optional[str] = None


class CreditTransactionOut(BaseModel):
    id: UUID
    tenant_id: UUID
    amount: int
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
