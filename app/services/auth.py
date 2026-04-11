from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from sqlalchemy.orm import Session
from app.config import settings
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.models.credit import CreditBalance
from app.schemas.auth import UserRegister

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_RESET_SALT = "sms-saas-pwd-reset"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def generate_reset_token(email: str, hashed_password: str) -> str:
    """Génère un token signé valable 1 heure pour la réinitialisation du mot de passe.
    Inclut une empreinte du hash courant pour invalider le token après usage."""
    s = URLSafeTimedSerializer(settings.SECRET_KEY)
    return s.dumps(
        {"email": email, "chk": hashed_password[-8:]},
        salt=_RESET_SALT,
    )


def verify_reset_token(token: str, max_age: int = 3600) -> tuple[str, str]:
    """Décode et vérifie le token. Retourne (email, chk) ou lève une exception."""
    s = URLSafeTimedSerializer(settings.SECRET_KEY)
    data = s.loads(token, salt=_RESET_SALT, max_age=max_age)
    return data["email"], data["chk"]


def register_user(db: Session, payload: UserRegister) -> User:
    tenant = Tenant(name=payload.company_name, slug=payload.slug)
    db.add(tenant)
    db.flush()

    user = User(
        tenant_id=tenant.id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.ADMIN
    )
    db.add(user)

    balance = CreditBalance(tenant_id=tenant.id, balance=0)
    db.add(balance)

    db.commit()
    db.refresh(user)

    # Email de bienvenue — non bloquant
    try:
        from app.services.email import send_welcome_email
        send_welcome_email(user.email, user.full_name or user.email)
    except Exception:
        pass

    return user


def authenticate_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user
