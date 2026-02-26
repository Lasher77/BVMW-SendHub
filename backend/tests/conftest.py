"""
Test configuration using an in-memory SQLite database so no Postgres is needed.
"""
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.settings import AppSettings
from app.models.department import Department
from app.models.user import User, UserRole
from app.models.campaign import Campaign, CampaignStatus

# SQLite in-memory
TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# SQLite does not support enums the same way; use String columns in tests via
# the SQLAlchemy native_enum=False mechanism — but since we're using the real
# models we need to disable native enums for SQLite.
# We override the engine's dialect before metadata creation.

TestSession = sessionmaker(bind=engine)


@pytest.fixture(scope="function")
def db():
    """Provide a transactional session backed by SQLite in-memory."""
    Base.metadata.create_all(bind=engine)
    session = TestSession()

    # Seed default settings
    if not session.query(AppSettings).first():
        session.add(AppSettings(id=1, min_gap_days=2))
        session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def dept(db):
    d = Department(name="Marketing-Test", is_active=True)
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


@pytest.fixture
def requester(db, dept):
    u = User(email="req@example.com", name="Requester", role=UserRole.requester, department_id=dept.id)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def moderator(db):
    u = User(email="mod@example.com", name="Moderator", role=UserRole.moderator, is_admin=False)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def admin(db):
    from app.auth import hash_password
    u = User(
        email="admin@example.com",
        name="Admin",
        role=UserRole.moderator,
        is_admin=True,
        password_hash=hash_password("testpass123"),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# Keep backward-compat alias for existing tests
@pytest.fixture
def marketer(db):
    u = User(email="mkt@example.com", name="Marketer", role=UserRole.moderator)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def make_campaign(db, title, send_at, status, creator_id, dept_id, channel="email") -> Campaign:
    c = Campaign(
        title=title,
        channel=channel,
        department_id=dept_id,
        status=status,
        send_at=send_at,
        created_by_id=creator_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c
