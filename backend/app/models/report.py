import uuid
from datetime import datetime, timezone, date

from sqlalchemy import String, ForeignKey, Date, Enum as SAEnum, JSON, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(
        SAEnum("lab", "diagnosis", "prescription", "discharge", name="report_type_enum"),
        nullable=False,
    )
    hospital: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department: Mapped[str | None] = mapped_column(String(50), nullable=True)
    report_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    images: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    extracted_indicators: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    hospital_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ocr_status: Mapped[str] = mapped_column(
        SAEnum("pending", "processing", "completed", "failed", name="ocr_status_enum"),
        nullable=False,
        default="pending",
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_report_member_date", "member_id", "report_date"),
    )
