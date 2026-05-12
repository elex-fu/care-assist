import uuid
from datetime import datetime, timezone, date

from sqlalchemy import String, ForeignKey, Date, Enum as SAEnum, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class VaccineRecord(Base):
    __tablename__ = "vaccine_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    vaccine_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dose: Mapped[int] = mapped_column(default=1)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum("completed", "pending", "upcoming", "overdue", name="vaccine_status_enum"),
        nullable=False,
        default="pending",
    )
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    batch_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reaction: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_custom: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_vaccine_member_status", "member_id", "status"),
        Index("idx_vaccine_scheduled", "scheduled_date"),
    )
