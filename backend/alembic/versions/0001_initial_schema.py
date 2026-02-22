"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # user_role enum
    op.execute("CREATE TYPE user_role AS ENUM ('requester', 'marketing')")
    # campaign_status enum
    op.execute(
        "CREATE TYPE campaign_status AS ENUM "
        "('submitted', 'in_review', 'changes_needed', 'scheduled', 'approved', 'rejected', 'sent')"
    )

    # departments
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
    )

    # users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("requester", "marketing", name="user_role"), nullable=False),
        sa.Column("department_id", sa.Integer, nullable=True),
    )

    # app_settings (singleton)
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("min_gap_days", sa.Integer, nullable=False, server_default="2"),
    )

    # campaigns
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False, server_default="email"),
        sa.Column("department_id", sa.Integer, sa.ForeignKey("departments.id"), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "submitted", "in_review", "changes_needed", "scheduled",
                "approved", "rejected", "sent",
                name="campaign_status",
            ),
            nullable=False,
            server_default="submitted",
        ),
        sa.Column("send_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # campaign_files
    op.create_table(
        "campaign_files",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("campaign_id", sa.Integer, sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("uploaded_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    )

    # campaign_assets
    op.create_table(
        "campaign_assets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("campaign_id", sa.Integer, sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("sanitized_filename", sa.String(500), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("uploaded_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    )

    # campaign_comments
    op.create_table(
        "campaign_comments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("campaign_id", sa.Integer, sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("author_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # campaign_move_logs
    op.create_table(
        "campaign_move_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("campaign_id", sa.Integer, sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("moved_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("old_send_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("new_send_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Indexes
    op.create_index("ix_campaigns_status", "campaigns", ["status"])
    op.create_index("ix_campaigns_send_at", "campaigns", ["send_at"])
    op.create_index("ix_campaigns_channel", "campaigns", ["channel"])
    op.create_index("ix_campaigns_department_id", "campaigns", ["department_id"])
    op.create_index("ix_campaigns_created_by_id", "campaigns", ["created_by_id"])


def downgrade() -> None:
    op.drop_table("campaign_move_logs")
    op.drop_table("campaign_comments")
    op.drop_table("campaign_assets")
    op.drop_table("campaign_files")
    op.drop_table("campaigns")
    op.drop_table("app_settings")
    op.drop_table("users")
    op.drop_table("departments")
    op.execute("DROP TYPE IF EXISTS campaign_status")
    op.execute("DROP TYPE IF EXISTS user_role")
