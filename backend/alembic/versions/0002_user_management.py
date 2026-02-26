"""Add user management fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-26 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'moderator' value to user_role enum (PostgreSQL)
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'moderator'")

    # Migrate existing 'marketing' users to 'moderator'
    op.execute("UPDATE users SET role = 'moderator' WHERE role = 'marketing'")

    # Add new columns
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean, nullable=False, server_default="false"),
    )
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )


def downgrade() -> None:
    op.drop_column("users", "is_active")
    op.drop_column("users", "is_admin")
    op.drop_column("users", "password_hash")

    # Migrate back to 'marketing'
    op.execute("UPDATE users SET role = 'marketing' WHERE role = 'moderator'")
    # Note: Cannot remove enum values in PostgreSQL
