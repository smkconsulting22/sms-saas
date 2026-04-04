import httpx
import redis
import base64
from app.config import settings

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
        return cached

    auth_header = _get_authorization_header()
    
    # Log temporaire pour déboguer
    print(f"CLIENT_ID: '{settings.ORANGE_CLIENT_ID}'")
    print(f"CLIENT_SECRET: '{settings.ORANGE_CLIENT_SECRET}'")
    print(f"AUTH HEADER: '{auth_header}'")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            ORANGE_TOKEN_URL,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            },
            data={"grant_type": "client_credentials"}
        )
        
        print(f"STATUS: {response.status_code}")
        print(f"RESPONSE: {response.text}")
        
        response.raise_for_status()
        data = response.json()

    token = data["access_token"]
    expires_in = data.get("expires_in", 3600)
    redis_client.setex(TOKEN_CACHE_KEY, expires_in - 300, token)

    return token