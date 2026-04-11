from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.routers import auth, sms, contacts, campaigns, credits, tenants, recharge, account_requests
from app.dependencies import limiter
from app.config import settings
from app.logging_config import setup_logging

setup_logging()

# ── Sentry (optionnel — actif uniquement si SENTRY_DSN est défini) ────────────
if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=0.2,
        environment="production",
    )

app = FastAPI(
    title="SMS SaaS API",
    description="Plateforme d'envoi de SMS via Orange",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://sms-saas-frontend-production.up.railway.app",
    ],
    # allow_origins=[
    #     "http://localhost:5173",
    #     "http://localhost:5174",
    #     "http://localhost:3000",
    #     "https://*.railway.app",
    #     "https://*.up.railway.app",
    #     "https://sms-saas-frontend-production.up.railway.app",
    #     "https://sms-saas-frontend.pages.dev",
    #     "*"
    # ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sms.router)
app.include_router(contacts.router)
app.include_router(campaigns.router)
app.include_router(credits.router)
app.include_router(tenants.router)
app.include_router(recharge.router)
app.include_router(account_requests.router)


@app.get("/")
def root():
    return {"status": "ok", "message": "SMS SaaS API"}


@app.get("/health")
def health():
    """Vérifie l'état de chaque service. Retourne 'degraded' sans crasher."""
    import redis as redis_lib
    from sqlalchemy import text
    from app.database import engine

    db_status = "ok"
    redis_status = "ok"
    overall = "healthy"

    # ── PostgreSQL ────────────────────────────────────────────────────────────
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {str(exc)[:80]}"
        overall = "degraded"

    # ── Redis ─────────────────────────────────────────────────────────────────
    try:
        r = redis_lib.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        r.ping()
    except Exception as exc:
        redis_status = f"error: {str(exc)[:80]}"
        overall = "degraded"

    return {
        "status": overall,
        "database": db_status,
        "redis": redis_status,
        "version": "1.0.0",
    }
