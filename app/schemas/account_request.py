from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class AccountRequestCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    company_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(default=None, min_length=8, max_length=20)
    message: Optional[str] = Field(default=None, max_length=500)


class AccountRequestOut(BaseModel):
    id: UUID
    full_name: str
    company_name: str
    email: str
    phone: Optional[str] = None
    message: Optional[str]
    status: str
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AccountRejectRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=255)
