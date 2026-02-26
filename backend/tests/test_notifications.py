"""
Tests für den Notification-Service und die E-Mail-Templates.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.models.campaign import Campaign, CampaignStatus
from app.models.user import User, UserRole
from app.services.email_templates import (
    STATUS_LABELS,
    render_new_campaign,
    render_new_comment,
    render_status_change,
)
from app.services.notification_service import (
    notify_new_campaign,
    notify_new_comment,
    notify_status_change,
)
from tests.conftest import make_campaign


# --------------------------------------------------------------------------- #
# Template-Tests
# --------------------------------------------------------------------------- #
class TestStatusChangeTemplate:
    def test_contains_campaign_title(self):
        subject, html = render_status_change(
            campaign_title="April Newsletter",
            campaign_id=1,
            old_status="submitted",
            new_status="in_review",
            actor_name="Bernd Müller",
            reason=None,
            base_url="http://localhost:3000",
        )
        assert "April Newsletter" in subject
        assert "April Newsletter" in html

    def test_contains_german_status_labels(self):
        subject, html = render_status_change(
            campaign_title="NL",
            campaign_id=1,
            old_status="submitted",
            new_status="in_review",
            actor_name="Bernd",
            reason=None,
            base_url="http://localhost:3000",
        )
        assert "In Prüfung" in subject
        assert "Eingereicht" in html
        assert "In Prüfung" in html

    def test_contains_actor_name(self):
        _, html = render_status_change(
            campaign_title="NL",
            campaign_id=1,
            old_status="submitted",
            new_status="approved",
            actor_name="Anna Schmidt",
            reason=None,
            base_url="http://test",
        )
        assert "Anna Schmidt" in html

    def test_contains_reason_when_provided(self):
        _, html = render_status_change(
            campaign_title="NL",
            campaign_id=1,
            old_status="approved",
            new_status="scheduled",
            actor_name="Bernd",
            reason="Bitte Logo austauschen",
            base_url="http://test",
        )
        assert "Bitte Logo austauschen" in html
        assert "Begründung" in html

    def test_no_reason_when_none(self):
        _, html = render_status_change(
            campaign_title="NL",
            campaign_id=1,
            old_status="submitted",
            new_status="in_review",
            actor_name="Bernd",
            reason=None,
            base_url="http://test",
        )
        assert "Begründung" not in html

    def test_contains_campaign_link(self):
        _, html = render_status_change(
            campaign_title="NL",
            campaign_id=42,
            old_status="submitted",
            new_status="approved",
            actor_name="X",
            reason=None,
            base_url="http://example.com",
        )
        assert "http://example.com/campaigns/42" in html


class TestCommentTemplate:
    def test_contains_campaign_title_and_author(self):
        subject, html = render_new_comment(
            campaign_title="Mai Newsletter",
            campaign_id=5,
            comment_text="Sieht gut aus!",
            author_name="Anna",
            base_url="http://test",
        )
        assert "Mai Newsletter" in subject
        assert "Sieht gut aus!" in html
        assert "Anna" in html

    def test_contains_campaign_link(self):
        _, html = render_new_comment(
            campaign_title="NL",
            campaign_id=7,
            comment_text="OK",
            author_name="A",
            base_url="http://example.com",
        )
        assert "http://example.com/campaigns/7" in html


class TestNewCampaignTemplate:
    def test_contains_all_details(self):
        subject, html = render_new_campaign(
            campaign_title="Juni Newsletter",
            campaign_id=10,
            creator_name="Anna Müller",
            department_name="Kommunikation",
            send_at_str="15.06.2025 09:00 Uhr",
            base_url="http://test",
        )
        assert "Juni Newsletter" in subject
        assert "Anna Müller" in html
        assert "Kommunikation" in html
        assert "15.06.2025" in html

    def test_contains_campaign_link(self):
        _, html = render_new_campaign(
            campaign_title="NL",
            campaign_id=99,
            creator_name="X",
            department_name="Y",
            send_at_str="01.01.2025",
            base_url="http://example.com",
        )
        assert "http://example.com/campaigns/99" in html


class TestStatusLabels:
    def test_all_statuses_have_labels(self):
        for status in CampaignStatus:
            assert status.value in STATUS_LABELS, f"Missing label for {status.value}"


# --------------------------------------------------------------------------- #
# Notification-Service-Tests
# --------------------------------------------------------------------------- #
class TestNotifyStatusChange:
    @patch("app.services.notification_service._send_to_many")
    @patch("app.services.notification_service.settings")
    def test_sends_to_creator_and_marketing(
        self, mock_settings, mock_send, db, dept, requester, marketer
    ):
        mock_settings.EMAIL_NOTIFICATIONS_ENABLED = True
        mock_settings.APP_BASE_URL = "http://test"

        campaign = make_campaign(
            db, "Test NL", datetime(2025, 6, 1, tzinfo=timezone.utc),
            CampaignStatus.submitted, requester.id, dept.id,
        )
        campaign.creator = requester

        notify_status_change(
            db, campaign, CampaignStatus.submitted, CampaignStatus.in_review, marketer,
        )

        mock_send.assert_called_once()
        recipients = mock_send.call_args[0][0]
        assert requester.email in recipients
        # Marketer is the actor, so excluded
        assert marketer.email not in recipients

    @patch("app.services.notification_service._send_to_many")
    @patch("app.services.notification_service.settings")
    def test_excludes_actor_from_recipients(
        self, mock_settings, mock_send, db, dept, requester, marketer
    ):
        mock_settings.EMAIL_NOTIFICATIONS_ENABLED = True
        mock_settings.APP_BASE_URL = "http://test"

        # Add second marketer
        m2 = User(email="mkt2@example.com", name="Marketer2", role=UserRole.marketing)
        db.add(m2)
        db.commit()
        db.refresh(m2)

        campaign = make_campaign(
            db, "Test", datetime(2025, 6, 1, tzinfo=timezone.utc),
            CampaignStatus.submitted, requester.id, dept.id,
        )
        campaign.creator = requester

        notify_status_change(
            db, campaign, CampaignStatus.submitted, CampaignStatus.in_review, marketer,
        )

        mock_send.assert_called_once()
        recipients = mock_send.call_args[0][0]
        assert requester.email in recipients
        assert m2.email in recipients
        assert marketer.email not in recipients  # Actor excluded

    @patch("app.services.notification_service._send_to_many")
    @patch("app.services.notification_service.settings")
    def test_does_not_notify_when_actor_is_creator(
        self, mock_settings, mock_send, db, dept, requester
    ):
        """Wenn Requester eigene Kampagne ändert (changes_needed → submitted)."""
        mock_settings.EMAIL_NOTIFICATIONS_ENABLED = True
        mock_settings.APP_BASE_URL = "http://test"

        campaign = make_campaign(
            db, "Test", datetime(2025, 6, 1, tzinfo=timezone.utc),
            CampaignStatus.changes_needed, requester.id, dept.id,
        )
        campaign.creator = requester

        notify_status_change(
            db, campaign, CampaignStatus.changes_needed, CampaignStatus.submitted, requester,
        )

        # No marketing users exist, and actor==creator, so no one to notify
        mock_send.assert_not_called()

    @patch("app.services.notification_service._send_to_many")
    @patch("app.services.notification_service.settings")
    def test_skips_when_disabled(
        self, mock_settings, mock_send, db, dept, requester, marketer
    ):
        mock_settings.EMAIL_NOTIFICATIONS_ENABLED = False

        campaign = make_campaign(
            db, "Test", datetime(2025, 6, 1, tzinfo=timezone.utc),
            CampaignStatus.submitted, requester.id, dept.id,
        )
        campaign.creator = requester

        notify_status_change(
            db, campaign, CampaignStatus.submitted, CampaignStatus.in_review, marketer,
        )

        mock_send.assert_not_called()


class TestNotifyNewComment:
    @patch("app.services.notification_service._send_to_many")
    @patch("app.services.notification_service.settings")
    def test_marketing_comment_notifies_creator(
        self, mock_settings, mock_send, db, dept, requester, marketer
    ):
        mock_settings.EMAIL_NOTIFICATIONS_ENABLED = True
        mock_settings.APP_BASE_URL = "http://test"

        campaign = make_campaign(
            db, "Test", datetime(2025, 6, 1, tzinfo=timezone.utc),
            CampaignStatus.in_review, requester.id, dept.id,
        )
        campaign.creator = requester

        notify_new_comment(db, campaign, "Sieht gut aus", marketer)

        mock_send.assert_called_once()
        recipients = mock_send.call_args[0][0]
        assert requester.email in recipients
        assert marketer.email not in recipients

    @patch("app.services.notification_service._send_to_many")
    @patch("app.services.notification_service.settings")
    def test_creator_comment_notifies_marketing(
        self, mock_settings, mock_send, db, dept, requester, marketer
    ):
        mock_settings.EMAIL_NOTIFICATIONS_ENABLED = True
        mock_settings.APP_BASE_URL = "http://test"

        campaign = make_campaign(
            db, "Test", datetime(2025, 6, 1, tzinfo=timezone.utc),
            CampaignStatus.in_review, requester.id, dept.id,
        )
        campaign.creator = requester

        notify_new_comment(db, campaign, "PDF aktualisiert", requester)

        mock_send.assert_called_once()
        recipients = mock_send.call_args[0][0]
        assert marketer.email in recipients
        assert requester.email not in recipients

    @patch("app.services.notification_service._send_to_many")
    @patch("app.services.notification_service.settings")
    def test_skips_when_disabled(
        self, mock_settings, mock_send, db, dept, requester, marketer
    ):
        mock_settings.EMAIL_NOTIFICATIONS_ENABLED = False

        campaign = make_campaign(
            db, "Test", datetime(2025, 6, 1, tzinfo=timezone.utc),
            CampaignStatus.in_review, requester.id, dept.id,
        )
        campaign.creator = requester

        notify_new_comment(db, campaign, "Text", marketer)

        mock_send.assert_not_called()


class TestNotifyNewCampaign:
    @patch("app.services.notification_service._send_to_many")
    @patch("app.services.notification_service.settings")
    def test_notifies_all_marketing_users(
        self, mock_settings, mock_send, db, dept, requester, marketer
    ):
        mock_settings.EMAIL_NOTIFICATIONS_ENABLED = True
        mock_settings.APP_BASE_URL = "http://test"

        campaign = make_campaign(
            db, "Neuer NL", datetime(2025, 6, 1, tzinfo=timezone.utc),
            CampaignStatus.submitted, requester.id, dept.id,
        )
        campaign.creator = requester
        campaign.department = dept

        notify_new_campaign(db, campaign, requester)

        mock_send.assert_called_once()
        recipients = mock_send.call_args[0][0]
        assert marketer.email in recipients

    @patch("app.services.notification_service._send_to_many")
    @patch("app.services.notification_service.settings")
    def test_skips_when_disabled(
        self, mock_settings, mock_send, db, dept, requester, marketer
    ):
        mock_settings.EMAIL_NOTIFICATIONS_ENABLED = False

        campaign = make_campaign(
            db, "Neuer NL", datetime(2025, 6, 1, tzinfo=timezone.utc),
            CampaignStatus.submitted, requester.id, dept.id,
        )
        campaign.department = dept

        notify_new_campaign(db, campaign, requester)

        mock_send.assert_not_called()

    @patch("app.services.notification_service._send_to_many")
    @patch("app.services.notification_service.settings")
    def test_skips_when_no_marketing_users(
        self, mock_settings, mock_send, db, dept, requester
    ):
        """Keine Marketing-User vorhanden → keine Mail."""
        mock_settings.EMAIL_NOTIFICATIONS_ENABLED = True
        mock_settings.APP_BASE_URL = "http://test"

        # Marketer-Fixture nicht geladen → kein Marketing-User in DB
        campaign = make_campaign(
            db, "Neuer NL", datetime(2025, 6, 1, tzinfo=timezone.utc),
            CampaignStatus.submitted, requester.id, dept.id,
        )
        campaign.department = dept

        notify_new_campaign(db, campaign, requester)

        mock_send.assert_not_called()
