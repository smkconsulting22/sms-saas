from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.routers import auth, sms, contacts, campaigns, credits, tenants
from app.dependencies import limiter

app = FastAPI(
    title="SMS SaaS API",
    description="Plateforme d'envoi de SMS via Orange",
    version="0.1.0"
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
    #      "https://sms-saas-frontend.pages.dev",
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


@app.get("/")
def root():
    return {"status": "ok", "message": "SMS SaaS API"}


@app.get("/health")
def health():
    return {"status": "healthy"}
