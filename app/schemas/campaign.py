from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class CampaignCreate(BaseModel):
    name: str
    message: str
    scheduled_at: Optional[datetime] = None

class CampaignOut(BaseModel):
    id: UUID
    name: str
    message: str
    status: str
    total: int
    sent: int
    failed: int
    created_at: datetime

    class Config:
        from_attributes = True