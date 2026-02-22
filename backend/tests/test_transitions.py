"""
Tests for status transition validation.
"""
import pytest
from fastapi import HTTPException

from app.models.campaign import CampaignStatus
from app.models.user import UserRole
from app.services.campaign_service import assert_transition


class TestTransitions:
    # ---- Requester allowed ----
    def test_requester_changes_needed_to_submitted(self):
        assert_transition(CampaignStatus.changes_needed, CampaignStatus.submitted, UserRole.requester)

    # ---- Requester forbidden ----
    def test_requester_cannot_approve(self):
        with pytest.raises(HTTPException) as exc:
            assert_transition(CampaignStatus.submitted, CampaignStatus.approved, UserRole.requester)
        assert exc.value.status_code == 422

    def test_requester_cannot_schedule(self):
        with pytest.raises(HTTPException):
            assert_transition(CampaignStatus.submitted, CampaignStatus.scheduled, UserRole.requester)

    def test_requester_cannot_reject(self):
        with pytest.raises(HTTPException):
            assert_transition(CampaignStatus.submitted, CampaignStatus.rejected, UserRole.requester)

    # ---- Marketing allowed ----
    def test_marketing_submitted_to_in_review(self):
        assert_transition(CampaignStatus.submitted, CampaignStatus.in_review, UserRole.marketing)

    def test_marketing_submitted_to_changes_needed(self):
        assert_transition(CampaignStatus.submitted, CampaignStatus.changes_needed, UserRole.marketing)

    def test_marketing_submitted_to_scheduled(self):
        assert_transition(CampaignStatus.submitted, CampaignStatus.scheduled, UserRole.marketing)

    def test_marketing_submitted_to_approved(self):
        assert_transition(CampaignStatus.submitted, CampaignStatus.approved, UserRole.marketing)

    def test_marketing_submitted_to_rejected(self):
        assert_transition(CampaignStatus.submitted, CampaignStatus.rejected, UserRole.marketing)

    def test_marketing_in_review_to_scheduled(self):
        assert_transition(CampaignStatus.in_review, CampaignStatus.scheduled, UserRole.marketing)

    def test_marketing_scheduled_to_sent(self):
        assert_transition(CampaignStatus.scheduled, CampaignStatus.sent, UserRole.marketing)

    def test_marketing_approved_to_scheduled(self):
        assert_transition(CampaignStatus.approved, CampaignStatus.scheduled, UserRole.marketing)

    def test_marketing_approved_to_sent(self):
        assert_transition(CampaignStatus.approved, CampaignStatus.sent, UserRole.marketing)

    # ---- Terminal states forbidden ----
    def test_rejected_no_further_transitions(self):
        for target in CampaignStatus:
            with pytest.raises(HTTPException):
                assert_transition(CampaignStatus.rejected, target, UserRole.marketing)

    def test_sent_no_further_transitions(self):
        for target in CampaignStatus:
            with pytest.raises(HTTPException):
                assert_transition(CampaignStatus.sent, target, UserRole.marketing)

    # ---- Invalid combinations ----
    def test_marketing_cannot_go_submitted_to_submitted(self):
        with pytest.raises(HTTPException):
            assert_transition(CampaignStatus.submitted, CampaignStatus.submitted, UserRole.marketing)

    def test_marketing_cannot_go_changes_needed_to_approved(self):
        with pytest.raises(HTTPException):
            assert_transition(CampaignStatus.changes_needed, CampaignStatus.approved, UserRole.marketing)
