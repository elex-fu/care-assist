import uuid
from datetime import datetime, timezone, date
from typing import Optional

from sqlalchemy import String, ForeignKey, Date, Enum as SAEnum, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Member(Base):
    __tablename__ = "members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    family_id: Mapped[str] = mapped_column(String(36), ForeignKey("families.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str] = mapped_column(SAEnum("male", "female", name="gender_enum"), nullable=False)
    blood_type: Mapped[str | None] = mapped_column(
        SAEnum("A", "B", "AB", "O", name="blood_type_enum"), nullable=True
    )
    allergies: Mapped[list] = mapped_column(JSON, default=list)
    chronic_diseases: Mapped[list] = mapped_column(JSON, default=list)
    type: Mapped[str] = mapped_column(
        SAEnum("adult", "child", "elderly", name="member_type_enum"), nullable=False, default="adult"
    )
    role: Mapped[str] = mapped_column(
        SAEnum("creator", "member", name="member_role_enum"), nullable=False, default="member"
    )
    wx_openid: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subscription_status: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    family: Mapped["Family"] = relationship("Family", back_populates="members")

    __table_args__ = (
        Index("idx_member_family", "family_id"),
        Index("idx_member_wx_openid", "wx_openid"),
    )
