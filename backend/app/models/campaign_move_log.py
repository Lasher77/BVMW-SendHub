from sqlalchemy import Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from app.database import Base


class CampaignMoveLog(Base):
    __tablename__ = "campaign_move_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    moved_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    old_send_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    new_send_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    campaign = relationship("Campaign", back_populates="move_logs")
    moved_by = relationship("User")
