import uuid
from sqlalchemy import Column, Integer, Numeric, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class TenantPricing(Base):
    __tablename__ = "tenant_pricing"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), unique=True, nullable=False)

    # Segment tarifaire : boutique | pme | enterprise | custom
    tier = Column(String(20), nullable=False, default="custom")

    # Prix unitaire par SMS en FCFA (entier, ex : 25)
    price_per_sms = Column(Integer, nullable=False, default=25)

    # Nombre minimum de crédits par demande de rechargement
    min_recharge_credits = Column(Integer, nullable=False, default=100)

    # Remise en pourcentage (0.00 → 100.00)
    discount_percent = Column(Numeric(5, 2), nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tenant = relationship("Tenant")
