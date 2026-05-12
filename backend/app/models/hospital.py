import uuid
from datetime import datetime, timezone, date

from sqlalchemy import String, ForeignKey, Date, Enum as SAEnum, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class HospitalEvent(Base):
    __tablename__ = "hospital_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    hospital: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str | None] = mapped_column(String(50), nullable=True)
    admission_date: Mapped[date] = mapped_column(Date, nullable=False)
    discharge_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(String(200), nullable=True)
    doctor: Mapped[str | None] = mapped_column(String(50), nullable=True)
    key_nodes: Mapped[list] = mapped_column(JSON, default=list)
    watch_indicators: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(
        SAEnum("active", "discharged", name="hospital_status_enum"),
        nullable=False,
        default="active",
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_hospital_member_status", "member_id", "status"),
    )
