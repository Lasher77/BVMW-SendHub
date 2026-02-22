"""
Tests for validate_email_slot and next_available.
"""
from datetime import datetime, date, timedelta
import pytz
import pytest
from fastapi import HTTPException

from app.models.campaign import CampaignStatus
from app.services.schedule_service import validate_email_slot, next_available, BERLIN
from tests.conftest import make_campaign

BERLIN_TZ = pytz.timezone("Europe/Berlin")


def berlin(year, month, day, hour=9, minute=0) -> datetime:
    """Helper: return a timezone-aware datetime in Europe/Berlin."""
    return BERLIN_TZ.localize(datetime(year, month, day, hour, minute, 0))


# ============================================================
# validate_email_slot tests
# ============================================================

class TestValidateEmailSlot:
    def test_no_existing_campaigns_passes(self, db, dept, requester):
        """With no existing blocking campaigns any slot is valid."""
        candidate = berlin(2025, 6, 2)
        # Should not raise
        validate_email_slot(db, candidate)

    def test_gap_exactly_min_allowed(self, db, dept, requester):
        """Monday + 2 days = Wednesday: should pass."""
        anchor = berlin(2025, 6, 2)  # Monday
        make_campaign(db, "A", anchor, CampaignStatus.scheduled, requester.id, dept.id)

        candidate = berlin(2025, 6, 4)  # Wednesday (+2 days)
        validate_email_slot(db, candidate)  # should NOT raise

    def test_gap_one_day_rejected(self, db, dept, requester):
        """Monday + 1 day = Tuesday: should be rejected (gap < 2)."""
        anchor = berlin(2025, 6, 2)  # Monday
        make_campaign(db, "A", anchor, CampaignStatus.scheduled, requester.id, dept.id)

        candidate = berlin(2025, 6, 3)  # Tuesday (+1 day)
        with pytest.raises(HTTPException) as exc_info:
            validate_email_slot(db, candidate)
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["code"] == "SLOT_CONFLICT"

    def test_same_day_rejected(self, db, dept, requester):
        """Same calendar day always conflicts (gap = 0 < 2)."""
        anchor = berlin(2025, 6, 5, 9)
        make_campaign(db, "A", anchor, CampaignStatus.approved, requester.id, dept.id)

        candidate = berlin(2025, 6, 5, 14)  # same day, different hour
        with pytest.raises(HTTPException) as exc_info:
            validate_email_slot(db, candidate)
        assert exc_info.value.status_code == 409

    def test_non_blocking_status_ignored(self, db, dept, requester):
        """Campaigns with non-blocking statuses do not count."""
        anchor = berlin(2025, 6, 2)
        make_campaign(db, "Draft", anchor, CampaignStatus.submitted, requester.id, dept.id)
        make_campaign(db, "Review", anchor, CampaignStatus.in_review, requester.id, dept.id)
        make_campaign(db, "Rejected", anchor, CampaignStatus.rejected, requester.id, dept.id)

        # Candidate on same day should still pass because none are blocking
        validate_email_slot(db, anchor)

    def test_sent_campaign_is_blocking(self, db, dept, requester):
        """Sent campaigns are blocking."""
        anchor = berlin(2025, 6, 2)
        make_campaign(db, "Sent", anchor, CampaignStatus.sent, requester.id, dept.id)

        candidate = berlin(2025, 6, 3)  # only +1 day
        with pytest.raises(HTTPException) as exc_info:
            validate_email_slot(db, candidate)
        assert exc_info.value.status_code == 409

    def test_self_exclusion(self, db, dept, requester):
        """
        When campaign_id is supplied the campaign is excluded from checks,
        allowing a reschedule to a date that would otherwise conflict with itself.
        """
        anchor = berlin(2025, 6, 2)
        c = make_campaign(db, "Self", anchor, CampaignStatus.scheduled, requester.id, dept.id)

        # Without exclusion: conflict
        with pytest.raises(HTTPException):
            validate_email_slot(db, anchor)

        # With exclusion: OK
        validate_email_slot(db, anchor, campaign_id=c.id)

    def test_multiple_campaigns_closest_determines_conflict(self, db, dept, requester):
        """Conflict is detected if any blocking campaign is within gap."""
        make_campaign(db, "Far", berlin(2025, 6, 1), CampaignStatus.scheduled, requester.id, dept.id)
        make_campaign(db, "Near", berlin(2025, 6, 8), CampaignStatus.approved, requester.id, dept.id)

        # June 9 is only +1 day from June 8 → conflict
        with pytest.raises(HTTPException):
            validate_email_slot(db, berlin(2025, 6, 9))

        # June 10 is +2 days from June 8 → OK
        validate_email_slot(db, berlin(2025, 6, 10))

    def test_non_email_channel_not_checked(self, db, dept, requester):
        """
        The gap rule applies only to channel='email'.
        Campaigns on other channels must not trigger conflicts.
        """
        anchor = berlin(2025, 6, 2)
        make_campaign(db, "SMS", anchor, CampaignStatus.scheduled, requester.id, dept.id, channel="sms")

        # Should not raise even though gap would be violated for email
        validate_email_slot(db, berlin(2025, 6, 3))

    def test_custom_min_gap(self, db, dept, requester):
        """Respects min_gap_days from app_settings."""
        from app.models.settings import AppSettings
        s = db.query(AppSettings).first()
        s.min_gap_days = 5
        db.commit()

        anchor = berlin(2025, 6, 1)
        make_campaign(db, "A", anchor, CampaignStatus.scheduled, requester.id, dept.id)

        # +4 days → conflict
        with pytest.raises(HTTPException):
            validate_email_slot(db, berlin(2025, 6, 5))

        # +5 days → OK
        validate_email_slot(db, berlin(2025, 6, 6))


# ============================================================
# next_available tests
# ============================================================

class TestNextAvailable:
    def test_no_campaigns_returns_today_or_tomorrow(self, db):
        """With no blocking campaigns, returns today or tomorrow at 09:00 Berlin."""
        result = next_available(db)
        berlin_now = datetime.now(BERLIN_TZ)
        assert result.tzinfo is not None
        berlin_result = result.astimezone(BERLIN_TZ)
        assert berlin_result.hour == 9
        assert berlin_result.minute == 0

        # Must be today or tomorrow
        today_date = berlin_now.date()
        result_date = berlin_result.date()
        assert result_date in (today_date, today_date + timedelta(days=1))

    def test_with_blocking_campaign(self, db, dept, requester):
        """Returns last_blocking_date + min_gap_days at 09:00."""
        anchor_date = date(2025, 6, 10)
        anchor = BERLIN_TZ.localize(datetime(2025, 6, 10, 9, 0))
        make_campaign(db, "Anchor", anchor, CampaignStatus.scheduled, requester.id, dept.id)

        result = next_available(db)
        berlin_result = result.astimezone(BERLIN_TZ)
        assert berlin_result.date() >= anchor_date + timedelta(days=2)
        assert berlin_result.hour == 9

    def test_respects_min_gap_setting(self, db, dept, requester):
        """next_available uses the configured min_gap_days."""
        from app.models.settings import AppSettings
        s = db.query(AppSettings).first()
        s.min_gap_days = 7
        db.commit()

        anchor = BERLIN_TZ.localize(datetime(2025, 6, 1, 9, 0))
        make_campaign(db, "A", anchor, CampaignStatus.approved, requester.id, dept.id)

        result = next_available(db).astimezone(BERLIN_TZ)
        assert result.date() >= date(2025, 6, 1) + timedelta(days=7)

    def test_multiple_campaigns_uses_latest(self, db, dept, requester):
        """Uses the latest blocking campaign as reference."""
        make_campaign(
            db, "Old", BERLIN_TZ.localize(datetime(2025, 5, 1, 9, 0)),
            CampaignStatus.sent, requester.id, dept.id,
        )
        make_campaign(
            db, "New", BERLIN_TZ.localize(datetime(2025, 6, 20, 9, 0)),
            CampaignStatus.approved, requester.id, dept.id,
        )

        result = next_available(db).astimezone(BERLIN_TZ)
        assert result.date() >= date(2025, 6, 20) + timedelta(days=2)

    def test_non_blocking_campaigns_ignored(self, db, dept, requester):
        """submitted/in_review/rejected campaigns do not push next_available date."""
        far_future = BERLIN_TZ.localize(datetime(2099, 12, 31, 9, 0))
        make_campaign(db, "Draft", far_future, CampaignStatus.submitted, requester.id, dept.id)
        make_campaign(db, "Review", far_future, CampaignStatus.in_review, requester.id, dept.id)

        result = next_available(db).astimezone(BERLIN_TZ)
        # Should be near today, not in 2099
        assert result.year < 2099

    def test_non_email_channel(self, db):
        """Non-email channel always returns today/tomorrow 09:00."""
        result = next_available(db, channel="sms")
        berlin_result = result.astimezone(BERLIN_TZ)
        assert berlin_result.hour == 9
        berlin_now = datetime.now(BERLIN_TZ)
        today_date = berlin_now.date()
        assert berlin_result.date() in (today_date, today_date + timedelta(days=1))
