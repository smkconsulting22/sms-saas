import uuid
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class RechargeRequest(Base):
    __tablename__ = "recharge_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    amount_requested = Column(Integer, nullable=False)
    amount_paid = Column(Numeric(10, 2), nullable=True)
    payment_method = Column(String(20), nullable=False)   # 'orange_money' | 'wave'
    payment_reference = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending | approved | rejected
    note = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tenant = relationship("Tenant")
