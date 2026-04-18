from pydantic import BaseModel, Field, field_validator
from typing import Optional
from decimal import Decimal
from datetime import datetime

VALID_TIERS = {"boutique", "pme", "enterprise", "custom"}

# Grille tarifaire de référence (FCFA/SMS)
TIER_DEFAULTS = {
    "boutique":   {"price_per_sms": 20, "min_recharge_credits": 100},
    "pme":        {"price_per_sms": 17, "min_recharge_credits": 500},
    "enterprise": {"price_per_sms": 12, "min_recharge_credits": 2000},
    "custom":     {"price_per_sms": 25, "min_recharge_credits": 100},
}


class TenantPricingSet(BaseModel):
    tier: str = Field(default="custom", description="boutique | pme | enterprise | custom")
    price_per_sms: int = Field(ge=1, le=999, description="Prix par SMS en FCFA")
    min_recharge_credits: int = Field(ge=1, description="Minimum de crédits par rechargement")
    discount_percent: Decimal = Field(
        default=Decimal("0"), ge=0, le=100,
        description="Remise en % (0 = aucune remise)",
    )

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v: str) -> str:
        if v not in VALID_TIERS:
            raise ValueError(f"Segment invalide. Valeurs acceptées : {', '.join(sorted(VALID_TIERS))}")
        return v


class TenantPricingOut(BaseModel):
    tenant_id: str
    tier: str
    price_per_sms: int
    min_recharge_credits: int
    discount_percent: Decimal
    # Prix effectif après remise
    effective_price_per_sms: Decimal
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
