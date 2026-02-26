from sqlalchemy import Boolean, String, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.database import Base


class UserRole(str, enum.Enum):
    requester = "requester"
    marketing = "marketing"  # legacy – kept for DB compatibility
    moderator = "moderator"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"), nullable=False, default=UserRole.requester
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    department_id: Mapped[int | None] = mapped_column(nullable=True)

    campaigns = relationship("Campaign", back_populates="creator", foreign_keys="Campaign.created_by_id")
    comments = relationship("CampaignComment", back_populates="author")

    @property
    def is_moderator(self) -> bool:
        return self.role in (UserRole.moderator, UserRole.marketing)
