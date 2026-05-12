import uuid
from datetime import datetime, timezone

from typing import TYPE_CHECKING

from sqlalchemy import String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.member import Member


class Family(Base):
    __tablename__ = "families"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="我的家庭")
    admin_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    invite_code: Mapped[str | None] = mapped_column(String(10), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    members: Mapped[list["Member"]] = relationship("Member", back_populates="family")

    __table_args__ = (
        Index("idx_invite_code", "invite_code"),
    )
