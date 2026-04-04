import httpx
import phonenumbers
from app.services.orange_token import get_orange_token
from app.config import settings

ORANGE_SMS_URL = "https://api.orange.com/smsmessaging/v1"

def format_number(number: str) -> str:
    """Formate un numéro en E.164 ex: +2250700000000"""
    parsed = phonenumbers.parse(number, "CI")
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError(f"Numéro invalide : {number}")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

def get_sender_address() -> str:
    """Retourne le senderAddress sans + pour l'URL"""
    return settings.ORANGE_SENDER_NUMBER.replace("+", "")

async def send_sms(recipient: str, message: str) -> dict:
    token = await get_orange_token()
    formatted_recipient = format_number(recipient)
    sender = get_sender_address()

    url = f"{ORANGE_SMS_URL}/outbound/tel:+{sender}/requests"

    payload = {
        "outboundSMSMessageRequest": {
            "address": f"tel:{formatted_recipient}",
            "senderAddress": f"tel:+{sender}",
            "senderName":"RESAFIG",
            "outboundSMSTextMessage": {
                "message": message
            }
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )

        # Si token expiré, vider le cache et réessayer
        if response.status_code == 401:
            from redis import Redis
            redis_client = Redis.from_url(settings.REDIS_URL)
            redis_client.delete("orange_access_token")
            token = await get_orange_token()
            response = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )

        response.raise_for_status()
        return response.json()