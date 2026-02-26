"""
Tests for user management model operations.
"""
import pytest
from app.auth import hash_password
from app.models.user import User, UserRole


class TestUserModel:
    def test_is_moderator_for_moderator_role(self, db, moderator):
        assert moderator.is_moderator

    def test_is_moderator_for_legacy_marketing_role(self, db):
        u = User(email="legacy@example.com", name="Legacy", role=UserRole.marketing)
        db.add(u)
        db.commit()
        db.refresh(u)
        assert u.is_moderator

    def test_is_moderator_false_for_requester(self, db, requester):
        assert not requester.is_moderator

    def test_admin_flag(self, db, admin):
        assert admin.is_admin
        assert admin.is_moderator

    def test_default_values(self, db):
        u = User(email="new@example.com", name="New User", role=UserRole.moderator)
        db.add(u)
        db.commit()
        db.refresh(u)
        assert u.is_active is True
        assert u.is_admin is False
        assert u.password_hash is None

    def test_create_moderator_with_password(self, db):
        u = User(
            email="mod2@example.com",
            name="Mod Two",
            role=UserRole.moderator,
            password_hash=hash_password("securePass1"),
            is_admin=False,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        assert u.password_hash is not None
        assert u.role == UserRole.moderator

    def test_deactivate_user(self, db, moderator):
        moderator.is_active = False
        db.commit()
        db.refresh(moderator)
        assert not moderator.is_active

    def test_unique_email(self, db, moderator):
        from sqlalchemy.exc import IntegrityError
        u = User(email=moderator.email, name="Duplicate", role=UserRole.moderator)
        db.add(u)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
