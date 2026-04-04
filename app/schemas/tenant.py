from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
