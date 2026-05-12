import uuid
from datetime import datetime, timezone, date

from sqlalchemy import String, ForeignKey, Date, Enum as SAEnum, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(
        SAEnum("vaccine", "checkup", "review", "medication", name="reminder_type_enum"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum("pending", "completed", "overdue", name="reminder_status_enum"),
        nullable=False,
        default="pending",
    )
    completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    related_indicator: Mapped[str | None] = mapped_column(String(50), nullable=True)
    related_report_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    priority: Mapped[str] = mapped_column(
        SAEnum("critical", "high", "normal", "low", name="reminder_priority_enum"),
        nullable=False,
        default="normal",
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_reminder_member_status", "member_id", "status"),
        Index("idx_reminder_scheduled", "scheduled_date"),
    )
