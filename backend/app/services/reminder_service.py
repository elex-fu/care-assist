"""Reminder creation helpers."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder import Reminder
from app.models.report import Report


async def find_duplicate_reminder(
    db: AsyncSession,
    member_id: str,
    type: str,
    scheduled_date: date,
    related_report_id: str | None,
    related_indicator: str | None,
) -> Reminder | None:
    """Find an existing pending reminder that matches the dedup window.

    A duplicate is defined by the same member_id, type, related_report_id,
    related_indicator and a scheduled_date within one day of the provided date.
    """
    min_date = scheduled_date - timedelta(days=1)
    max_date = scheduled_date + timedelta(days=1)
    stmt = (
        select(Reminder)
        .where(
            Reminder.member_id == member_id,
            Reminder.type == type,
            Reminder.status == "pending",
            Reminder.related_report_id == related_report_id,
            Reminder.related_indicator == related_indicator,
            Reminder.scheduled_date >= min_date,
            Reminder.scheduled_date <= max_date,
        )
        .order_by(Reminder.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_reminder_from_report(
    db: AsyncSession, report: Report, scheduled_date: date
) -> Reminder:
    """Create a review reminder tied to a report."""
    summary = report.ai_summary or f"{report.type}报告"
    reminder = Reminder(
        member_id=report.member_id,
        type="review",
        title=f"复查提醒：{summary[:30]}",
        description=f"基于报告 {report.id} 生成的复查提醒",
        scheduled_date=scheduled_date,
        status="pending",
        related_report_id=report.id,
        priority="normal",
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return reminder
