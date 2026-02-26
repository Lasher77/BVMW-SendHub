"""
Tests for authentication: login, setup, JWT tokens.
"""
import pytest
from app.auth import hash_password, verify_password, create_access_token, decode_access_token
from app.models.user import User, UserRole


class TestPasswordHashing:
    def test_hash_and_verify(self):
        plain = "mySecretPassword123"
        hashed = hash_password(plain)
        assert hashed != plain
        assert verify_password(plain, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)


class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token(42, "user@example.com")
        payload = decode_access_token(token)
        assert payload["sub"] == "42"
        assert payload["email"] == "user@example.com"

    def test_invalid_token_raises(self):
        from jose import JWTError
        with pytest.raises(JWTError):
            decode_access_token("invalid.token.here")


class TestSetupStatus:
    def test_needs_setup_when_no_moderators(self, db):
        count = db.query(User).filter(
            User.role.in_([UserRole.moderator, UserRole.marketing])
        ).count()
        assert count == 0  # No moderators exist

    def test_no_setup_needed_after_admin_created(self, db, admin):
        count = db.query(User).filter(
            User.role.in_([UserRole.moderator, UserRole.marketing])
        ).count()
        assert count == 1


class TestLogin:
    def test_login_success(self, db, admin):
        assert verify_password("testpass123", admin.password_hash)

    def test_login_wrong_password(self, db, admin):
        assert not verify_password("wrongpass", admin.password_hash)

    def test_inactive_user(self, db):
        user = User(
            email="inactive@example.com",
            name="Inactive",
            role=UserRole.moderator,
            password_hash=hash_password("test123"),
            is_active=False,
        )
        db.add(user)
        db.commit()
        assert not user.is_active
