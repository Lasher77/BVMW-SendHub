"""
Auth helper.

Dev mode: reads X-User header (email address).
Prod mode: JWT Bearer token validation.

The X-User header is only trusted when ENVIRONMENT=development.
"""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Header, Request
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.config import settings

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours


def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------
def get_current_user(
    request: Request,
    x_user: str | None = Header(default=None, alias="X-User"),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    # Dev mode: trust X-User header
    if settings.ENVIRONMENT == "development" and x_user:
        user = db.query(User).filter(User.email == x_user).first()
        if not user:
            raise HTTPException(status_code=401, detail=f"User '{x_user}' not found.")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Benutzerkonto deaktiviert.")
        return user

    # Prod mode (or dev mode without X-User): JWT Bearer token
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            payload = decode_access_token(token)
            user_id = int(payload["sub"])
        except (JWTError, KeyError, ValueError):
            raise HTTPException(status_code=401, detail="Ungültiger Token.")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="Benutzer nicht gefunden.")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Benutzerkonto deaktiviert.")
        return user

    raise HTTPException(status_code=401, detail="Authentifizierung erforderlich.")


def require_moderator(user: User = Depends(get_current_user)) -> User:
    if not user.is_moderator:
        raise HTTPException(status_code=403, detail="Moderator-Rolle erforderlich.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_moderator or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Berechtigung erforderlich.")
    return user


# Keep backward compatibility alias
require_marketing = require_moderator
