import uuid
from datetime import datetime, timezone, date, time
from decimal import Decimal

from sqlalchemy import String, ForeignKey, Date, Time, Numeric, Enum as SAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class IndicatorData(Base):
    __tablename__ = "indicator_data"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    indicator_key: Mapped[str] = mapped_column(String(50), nullable=False)
    indicator_name: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    lower_limit: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    upper_limit: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum("normal", "low", "high", "critical", name="indicator_status_enum"),
        nullable=False,
    )
    deviation_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    record_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    source_report_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_hospital_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_batch_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_indicator_member_date", "member_id", "record_date"),
        Index("idx_indicator_member_key_date", "member_id", "indicator_key", "record_date"),
        Index("idx_indicator_status", "status"),
    )
