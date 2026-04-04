from pydantic import BaseModel

class SMSSend(BaseModel):
    recipient: str
    message: str

class SMSResponse(BaseModel):
    status: str
    recipient: str
    message_id: str | None = None