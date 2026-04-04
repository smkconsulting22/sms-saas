from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, sms, contacts, campaigns

app = FastAPI(
    title="SMS SaaS API",
    description="Plateforme d'envoi de SMS via Orange",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://*.railway.app",
        "https://*.up.railway.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sms.router)
app.include_router(contacts.router)
app.include_router(campaigns.router)


@app.get("/")
def root():
    return {"status": "ok", "message": "SMS SaaS API"}


@app.get("/health")
def health():
    return {"status": "healthy"}