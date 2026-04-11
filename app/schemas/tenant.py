import re
from pydantic import BaseModel, field_validator
from typing import Optional

_SENDER_NAME_RE = re.compile(r'^[a-zA-Z0-9]{1,11}$')


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class SenderNameUpdate(BaseModel):
    sender_name: str

    @field_validator('sender_name')
    @classmethod
    def validate_sender_name(cls, v: str) -> str:
        if not _SENDER_NAME_RE.match(v):
            raise ValueError(
                'sender_name doit contenir 1 à 11 caractères alphanumériques uniquement (a-z, A-Z, 0-9)'
            )
        return v
