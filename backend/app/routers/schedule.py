from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.schedule_service import next_available, get_move_options

router = APIRouter(tags=["schedule"])


@router.get("/schedule/next-available")
def get_next_available(
    channel: str = Query(default="email"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    dt = next_available(db, channel=channel)
    return {"next_available": dt.isoformat()}


@router.get("/campaigns/{campaign_id}/move-options")
def campaign_move_options(
    campaign_id: int,
    start: date = Query(...),
    end: date = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    valid = get_move_options(db, campaign_id=campaign_id, start=start, end=end)
    return {"valid_dates": [d.isoformat() for d in valid]}
