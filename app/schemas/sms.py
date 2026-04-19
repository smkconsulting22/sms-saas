from pydantic import BaseModel
from typing import Optional

class SMSSend(BaseModel):
    recipient: str
    message: str

class SMSResponse(BaseModel):
    status: str
    recipient: str
    message_id: Optional[str] = None