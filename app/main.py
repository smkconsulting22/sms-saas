from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.models import Tenant, User, CreditBalance, CreditTransaction
from app.models import Contact, Campaign, CampaignLog
from app.routers import auth, sms, contacts, campaigns

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SMS SaaS API",
    description="Plateforme d'envoi de SMS via Orange",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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