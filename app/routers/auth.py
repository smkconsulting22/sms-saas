import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from itsdangerous import SignatureExpired, BadSignature
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import (
    UserRegister, Token, MakeSuperAdminRequest,
    ForgotPasswordRequest, ResetPasswordRequest,
)
from app.services.auth import (
    register_user, authenticate_user, create_access_token,
    generate_reset_token, verify_reset_token, hash_password,
)
from app.services.email import send_password_reset_email
from app.models.user import User
from app.config import settings
from app.dependencies import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
def register(request: Request, payload: UserRegister, db: Session = Depends(get_db)):
    """Inscription directe désactivée. Passer par POST /account-requests/ à la place."""
    raise HTTPException(
        status_code=403,
        detail="Les inscriptions directes sont fermées. Soumettez une demande de compte via /account-requests/.",
    )


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form.username, form.password)
    if not user:
        logger.warning("Échec connexion pour email=%s", form.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    logger.info("Connexion réussie user=%s tenant=%s", user.email, user.tenant_id)
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


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Génère un lien de réinitialisation et l'envoie par email.
    Retourne toujours 200 même si l'email est inconnu (sécurité)."""
    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        token = generate_reset_token(user.email, user.hashed_password)
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        send_password_reset_email(user.email, user.full_name or user.email, reset_url)
    return {"message": "Si cet email existe, un lien de réinitialisation a été envoyé."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Vérifie le token et met à jour le mot de passe. Invalide le token après usage."""
    try:
        email, chk = verify_reset_token(payload.token)
    except SignatureExpired:
        raise HTTPException(status_code=400, detail="Le lien de réinitialisation a expiré")
    except (BadSignature, Exception):
        raise HTTPException(status_code=400, detail="Lien de réinitialisation invalide")

    user = db.query(User).filter(User.email == email).first()
    if not user or user.hashed_password[-8:] != chk:
        raise HTTPException(status_code=400, detail="Lien invalide ou déjà utilisé")

    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"message": "Mot de passe mis à jour avec succès"}
