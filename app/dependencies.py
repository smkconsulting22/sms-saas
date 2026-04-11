from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

limiter = Limiter(key_func=get_remote_address)


def get_current_tenant(token: str = Depends(oauth2_scheme)) -> dict:
    """Décode le token JWT et retourne le payload."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")


def require_superadmin(current: dict = Depends(get_current_tenant)) -> dict:
    """Réservé aux super administrateurs (is_superadmin=True)."""
    if not current.get("is_superadmin"):
        raise HTTPException(status_code=403, detail="Accès réservé aux super administrateurs")
    return current


def require_admin(current: dict = Depends(get_current_tenant)) -> dict:
    """Réservé aux admins du tenant ou aux super administrateurs."""
    if current.get("role") != "admin" and not current.get("is_superadmin"):
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    return current
