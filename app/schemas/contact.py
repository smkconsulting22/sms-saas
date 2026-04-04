from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class ContactCreate(BaseModel):
    phone: str
    full_name: Optional[str] = None

class ContactOut(BaseModel):
    id: UUID
    phone: str
    full_name: Optional[str]
    is_optout: bool

    class Config:
        from_attributes = True