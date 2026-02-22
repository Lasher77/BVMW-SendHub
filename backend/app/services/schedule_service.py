"""
Schedule service: min-gap validation and next-available slot calculation.

All date arithmetic is performed in the Europe/Berlin timezone.
Gap rule:  abs(date_a - date_b) in calendar days >= min_gap_days
  gap=2: Monday → Wednesday OK, Monday → Tuesday NOT OK.
"""
from datetime import datetime, timedelta, date
from typing import Optional
import pytz
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.campaign import Campaign, BLOCKING_STATUSES, CampaignStatus

BERLIN = pytz.timezone("Europe/Berlin")


def _to_berlin_date(dt: datetime) -> date:
    """Convert an aware or naive datetime to a date in Europe/Berlin."""
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(BERLIN).date()


def _get_min_gap(db: Session) -> int:
    from app.models.settings import AppSettings
    s = db.query(AppSettings).first()
    return s.min_gap_days if s else 2


def validate_email_slot(
    db: Session,
    candidate_send_at: datetime,
    campaign_id: Optional[int] = None,
) -> None:
    """
    Validate that candidate_send_at does not violate the min-gap rule for
    channel='email'.  Raises HTTP 409 on conflict.

    :param db: SQLAlchemy session
    :param candidate_send_at: proposed send datetime (timezone-aware preferred)
    :param campaign_id: if provided, the campaign being rescheduled is excluded
                        from conflict checks (so it doesn't conflict with itself)
    """
    min_gap = _get_min_gap(db)
    candidate_date = _to_berlin_date(candidate_send_at)

    q = db.query(Campaign).filter(
        Campaign.channel == "email",
        Campaign.status.in_([s.value for s in BLOCKING_STATUSES]),
        Campaign.send_at.isnot(None),
    )
    if campaign_id is not None:
        q = q.filter(Campaign.id != campaign_id)

    for c in q.all():
        existing_date = _to_berlin_date(c.send_at)
        gap = abs((candidate_date - existing_date).days)
        if gap < min_gap:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "SLOT_CONFLICT",
                    "message": (
                        f"Mindestabstand von {min_gap} Tagen nicht eingehalten. "
                        f"Konflikt mit Kampagne '{c.title}' (ID {c.id}) am "
                        f"{existing_date.isoformat()}."
                    ),
                    "conflicting_campaign_id": c.id,
                    "conflicting_date": existing_date.isoformat(),
                    "min_gap_days": min_gap,
                },
            )


def next_available(db: Session, channel: str = "email") -> datetime:
    """
    Compute the next available send slot.

    Algorithm:
    1. Find the latest send_at among blocking campaigns (same channel).
    2. next_date = last_date + min_gap_days.
    3. If no blocking campaigns: today at 09:00 Berlin; if that is in the past,
       tomorrow at 09:00 Berlin.
    """
    if channel != "email":
        # For non-email channels there is no gap restriction; return today/tomorrow 09:00
        now_berlin = datetime.now(BERLIN)
        candidate = now_berlin.replace(hour=9, minute=0, second=0, microsecond=0)
        if candidate <= now_berlin:
            candidate += timedelta(days=1)
        return candidate

    min_gap = _get_min_gap(db)

    latest: Optional[Campaign] = (
        db.query(Campaign)
        .filter(
            Campaign.channel == channel,
            Campaign.status.in_([s.value for s in BLOCKING_STATUSES]),
            Campaign.send_at.isnot(None),
        )
        .order_by(Campaign.send_at.desc())
        .first()
    )

    now_berlin = datetime.now(BERLIN)

    if latest is None:
        candidate = now_berlin.replace(hour=9, minute=0, second=0, microsecond=0)
        if candidate <= now_berlin:
            candidate = candidate + timedelta(days=1)
        return candidate

    last_date = _to_berlin_date(latest.send_at)
    next_date = last_date + timedelta(days=min_gap)

    # Build a timezone-aware datetime at 09:00 Berlin on next_date
    candidate = BERLIN.localize(datetime(next_date.year, next_date.month, next_date.day, 9, 0, 0))

    # Ensure candidate is not in the past
    if candidate <= now_berlin:
        # Recalculate from now
        today_09 = now_berlin.replace(hour=9, minute=0, second=0, microsecond=0)
        if today_09 <= now_berlin:
            today_09 += timedelta(days=1)
        candidate = max(candidate, today_09)

    return candidate


def get_move_options(
    db: Session,
    campaign_id: int,
    start: date,
    end: date,
) -> list[date]:
    """
    Return a list of dates in [start, end] that are valid send-date candidates
    for the given campaign (channel='email').
    """
    valid_dates = []
    current = start
    while current <= end:
        candidate_dt = BERLIN.localize(
            datetime(current.year, current.month, current.day, 9, 0, 0)
        )
        try:
            validate_email_slot(db, candidate_dt, campaign_id=campaign_id)
            valid_dates.append(current)
        except HTTPException:
            pass
        current += timedelta(days=1)
    return valid_dates
