from sqlalchemy import String, Enum as SAEnum, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import enum
from app.database import Base


class CampaignStatus(str, enum.Enum):
    submitted = "submitted"
    in_review = "in_review"
    changes_needed = "changes_needed"
    scheduled = "scheduled"
    approved = "approved"
    rejected = "rejected"
    sent = "sent"


# Statuses that block a time slot for min-gap calculation
BLOCKING_STATUSES = {
    CampaignStatus.scheduled,
    CampaignStatus.approved,
    CampaignStatus.sent,
}


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False, default="email")
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)
    status: Mapped[CampaignStatus] = mapped_column(
        SAEnum(CampaignStatus, name="campaign_status"),
        nullable=False,
        default=CampaignStatus.submitted,
    )
    send_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    department = relationship("Department", back_populates="campaigns")
    creator = relationship("User", back_populates="campaigns", foreign_keys=[created_by_id])
    files = relationship("CampaignFile", back_populates="campaign", order_by="CampaignFile.version")
    assets = relationship("CampaignAsset", back_populates="campaign")
    comments = relationship("CampaignComment", back_populates="campaign", order_by="CampaignComment.created_at")
    move_logs = relationship("CampaignMoveLog", back_populates="campaign", order_by="CampaignMoveLog.created_at")
