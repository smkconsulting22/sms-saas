import logging
import httpx
import redis
import base64
from app.config import settings

logger = logging.getLogger(__name__)

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

TOKEN_CACHE_KEY = "orange_access_token"
ORANGE_TOKEN_URL = "https://api.orange.com/oauth/v3/token"


def _get_authorization_header() -> str:
    credentials = f"{settings.ORANGE_CLIENT_ID}:{settings.ORANGE_CLIENT_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


async def get_orange_token() -> str:
    cached = redis_client.get(TOKEN_CACHE_KEY)
    if cached:
        logger.debug("Orange token récupéré depuis le cache Redis")
        return cached

    logger.info("Récupération d'un nouveau token Orange API")
    auth_header = _get_authorization_header()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            ORANGE_TOKEN_URL,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={"grant_type": "client_credentials"},
        )

        if response.status_code != 200:
            logger.error(
                "Échec récupération token Orange : status=%s body=%s",
                response.status_code,
                response.text[:200],
            )
        response.raise_for_status()
        data = response.json()

    token = data["access_token"]
    expires_in = data.get("expires_in", 3600)
    redis_client.setex(TOKEN_CACHE_KEY, expires_in - 300, token)
    logger.info("Nouveau token Orange mis en cache pour %ds", expires_in - 300)

    return token
