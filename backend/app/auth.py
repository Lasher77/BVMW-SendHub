"""
Auth helper.

Dev mode: reads X-User header (email address).
Prod mode: OIDC token validation (placeholder for future integration).

The X-User header is only trusted when ENVIRONMENT=development.
"""
from fastapi import Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.config import settings


def get_current_user(
    request: Request,
    x_user: str | None = Header(default=None, alias="X-User"),
    db: Session = Depends(get_db),
) -> User:
    if settings.ENVIRONMENT == "development":
        if not x_user:
            raise HTTPException(status_code=401, detail="X-User header required in dev mode.")
        user = db.query(User).filter(User.email == x_user).first()
        if not user:
            raise HTTPException(status_code=401, detail=f"User '{x_user}' not found.")
        return user

    # OIDC placeholder
    raise HTTPException(status_code=501, detail="OIDC auth not yet configured.")


def require_marketing(user: User = Depends(get_current_user)) -> User:
    from app.models.user import UserRole
    if user.role != UserRole.marketing:
        raise HTTPException(status_code=403, detail="Marketing-Rolle erforderlich.")
    return user
