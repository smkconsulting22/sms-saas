from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import UserRegister, Token, MakeSuperAdminRequest
from app.services.auth import register_user, authenticate_user, create_access_token
from app.models.user import User
from app.config import settings
from app.dependencies import limiter

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
def register(request: Request, payload: UserRegister, db: Session = Depends(get_db)):
    try:
        user = register_user(db, payload)
        return {"message": "Compte créé", "user_id": str(user.id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form.username, form.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )
    token = create_access_token({
        "user_id": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role,
        "is_superadmin": user.is_superadmin,
    })
    return {"access_token": token, "token_type": "bearer"}


@router.post("/make-superadmin")
def make_superadmin(payload: MakeSuperAdminRequest, db: Session = Depends(get_db)):
    if payload.secret_key != settings.SECRET_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Clé secrète invalide")

    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    user.is_superadmin = True
    db.commit()
    return {"message": f"{payload.email} est maintenant super administrateur"}
