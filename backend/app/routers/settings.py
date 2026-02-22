from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_marketing
from app.database import get_db
from app.models.settings import AppSettings
from app.models.user import User
from app.schemas.settings import SettingsOut, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


def _get_or_create(db: Session) -> AppSettings:
    s = db.query(AppSettings).first()
    if not s:
        s = AppSettings(id=1, min_gap_days=2)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


@router.get("", response_model=SettingsOut)
def get_settings(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return _get_or_create(db)


@router.patch("", response_model=SettingsOut)
def update_settings(
    body: SettingsUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_marketing),
):
    s = _get_or_create(db)
    s.min_gap_days = body.min_gap_days
    db.commit()
    db.refresh(s)
    return s
