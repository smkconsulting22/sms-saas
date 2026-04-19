import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    sender_name = Column(String(11), nullable=True)
    sms_price = Column(Numeric(10, 2), nullable=False, server_default="20.0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sender_name_requested = Column(String(11), nullable=True)
    sender_name_status = Column(String(20), nullable=False, server_default="none")
    sender_name_requested_at = Column(DateTime(timezone=True), nullable=True)
    sender_name_approved_at = Column(DateTime(timezone=True), nullable=True)
    sender_name_rejection_reason = Column(Text, nullable=True)

    users = relationship("User", back_populates="tenant")