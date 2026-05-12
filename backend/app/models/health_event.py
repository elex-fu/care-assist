import uuid
from datetime import datetime, timezone, date, time

from sqlalchemy import String, ForeignKey, Date, Time, Enum as SAEnum, JSON, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class HealthEvent(Base):
    __tablename__ = "health_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(
        SAEnum(
            "visit", "lab", "medication", "symptom", "ai",
            "hospital", "vaccine", "checkup", "milestone",
            name="health_event_type_enum",
        ),
        nullable=False,
    )
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    event_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    hospital: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department: Mapped[str | None] = mapped_column(String(50), nullable=True)
    doctor: Mapped[str | None] = mapped_column(String(50), nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    hospital_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum("normal", "abnormal", name="health_event_status_enum"),
        nullable=False,
        default="normal",
    )
    abnormal_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_health_event_member_date", "member_id", "event_date"),
        Index("idx_health_event_type", "type"),
    )
