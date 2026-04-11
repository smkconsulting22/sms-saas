import asyncio
import logging
import httpx
import phonenumbers
from app.services.orange_token import get_orange_token
from app.config import settings

logger = logging.getLogger(__name__)

ORANGE_SMS_URL = "https://api.orange.com/smsmessaging/v1"

# Délais en secondes entre les tentatives (tentative 2 : 1s, tentative 3 : 3s)
_RETRY_DELAYS = [1, 3]


def format_number(number: str) -> str:
    """Formate un numéro en E.164, ex: +2250700000000."""
    parsed = phonenumbers.parse(number, "CI")
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError(f"Numéro invalide : {number}")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def get_sender_address() -> str:
    """Retourne le senderAddress sans + pour l'URL."""
    return settings.ORANGE_SENDER_NUMBER.replace("+", "")


async def _send_sms_once(formatted_recipient: str, message: str) -> dict:
    """Une tentative d'envoi : gère le token, la requête HTTP et le refresh 401."""
    token = await get_orange_token()
    sender = get_sender_address()
    url = f"{ORANGE_SMS_URL}/outbound/tel:+{sender}/requests"

    payload = {
        "outboundSMSMessageRequest": {
            "address": f"tel:{formatted_recipient}",
            "senderAddress": f"tel:+{sender}",
            "senderName": "RESAFIG",
            "outboundSMSTextMessage": {"message": message},
        }
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, json=payload, headers=headers)

        # Token expiré → vider le cache et réessayer une fois
        if response.status_code == 401:
            logger.warning("Token Orange expiré — renouvellement en cours")
            from redis import Redis
            Redis.from_url(settings.REDIS_URL).delete("orange_access_token")
            token = await get_orange_token()
            headers["Authorization"] = f"Bearer {token}"
            response = await client.post(url, json=payload, headers=headers)

        response.raise_for_status()
        return response.json()


async def send_sms(recipient: str, message: str, tenant_id: str = "") -> dict:
    """Envoie un SMS avec jusqu'à 3 tentatives.

    Délais entre tentatives : 1s puis 3s.
    Lève l'exception après 3 échecs consécutifs.
    """
    formatted_recipient = format_number(recipient)
    ctx = f"recipient={formatted_recipient} tenant={tenant_id or 'n/a'}"
    last_exc: Exception = RuntimeError("Aucune tentative effectuée")

    for attempt in range(1, 4):
        if attempt > 1:
            delay = _RETRY_DELAYS[attempt - 2]
            logger.info("SMS retry %d/3 dans %ds — %s", attempt, delay, ctx)
            await asyncio.sleep(delay)
        else:
            logger.info("SMS envoi tentative 1/3 — %s", ctx)

        try:
            result = await _send_sms_once(formatted_recipient, message)
            logger.info("SMS envoyé avec succès (tentative %d/3) — %s", attempt, ctx)
            return result
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            logger.warning(
                "SMS tentative %d/3 échouée — HTTP %s %s — %s",
                attempt,
                exc.response.status_code,
                exc.response.text[:100],
                ctx,
            )
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "SMS tentative %d/3 échouée — %s — %s",
                attempt,
                str(exc),
                ctx,
            )

    logger.error("SMS échec définitif après 3 tentatives — %s", ctx)
    raise last_exc
