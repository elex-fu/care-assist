
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.security import get_current_member, get_db
from app.models.member import Member
from app.models.reminder import Reminder
from app.models.report import Report
from app.schemas.common import ResponseWrapper
from app.schemas.reminder import (
    ReminderCreate,
    ReminderGenerateRequest,
    ReminderOut,
    ReminderUpdate,
)
from app.services.reminder_service import (
    create_reminder_from_report,
    find_duplicate_reminder,
)

router = APIRouter(prefix="/reminders", tags=["提醒系统"])


async def _verify_member_in_family(member_id: str, current: Member, db: AsyncSession) -> Member:
    target = await db.get(Member, member_id)
    if not target:
        raise NotFoundException("成员不存在")
    if target.family_id != current.family_id:
        raise ForbiddenException("无权限操作其他家庭的成员")
    return target


@router.post("", response_model=ResponseWrapper[ReminderOut])
async def create_reminder(
    payload: ReminderCreate,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    target = await _verify_member_in_family(payload.member_id, current, db)

    duplicate = await find_duplicate_reminder(
        db,
        member_id=target.id,
        type=payload.type,
        scheduled_date=payload.scheduled_date,
        related_report_id=payload.related_report_id,
        related_indicator=payload.related_indicator,
    )
    if duplicate:
        return ResponseWrapper(data=ReminderOut.model_validate(duplicate))

    reminder = Reminder(
        member_id=target.id,
        type=payload.type,
        title=payload.title,
        description=payload.description,
        scheduled_date=payload.scheduled_date,
        status=payload.status,
        related_indicator=payload.related_indicator,
        related_report_id=payload.related_report_id,
        priority=payload.priority,
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return ResponseWrapper(data=ReminderOut.model_validate(reminder))


@router.get("", response_model=ResponseWrapper[list[ReminderOut]])
async def list_reminders(
    member_id: str = Query(...),
    status: str | None = Query(None),
    type: str | None = Query(None),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await _verify_member_in_family(member_id, current, db)

    stmt = select(Reminder).where(Reminder.member_id == member_id)
    if status:
        stmt = stmt.where(Reminder.status == status)
    if type:
        stmt = stmt.where(Reminder.type == type)
    stmt = stmt.order_by(desc(Reminder.scheduled_date), desc(Reminder.created_at))

    result = await db.execute(stmt)
    items = result.scalars().all()
    return ResponseWrapper(data=[ReminderOut.model_validate(i) for i in items])


@router.post("/from-report", response_model=ResponseWrapper[ReminderOut])
async def create_from_report(
    payload: ReminderGenerateRequest,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """Create a review reminder from a report."""
    target = await _verify_member_in_family(payload.member_id, current, db)
    report = await db.get(Report, payload.report_id)
    if not report or report.member_id != target.id:
        raise NotFoundException("报告不存在")

    duplicate = await find_duplicate_reminder(
        db,
        member_id=target.id,
        type="review",
        scheduled_date=payload.scheduled_date,
        related_report_id=report.id,
        related_indicator=None,
    )
    if duplicate:
        return ResponseWrapper(data=ReminderOut.model_validate(duplicate))

    reminder = await create_reminder_from_report(db, report, payload.scheduled_date)
    return ResponseWrapper(data=ReminderOut.model_validate(reminder))


@router.patch("/{reminder_id}", response_model=ResponseWrapper[ReminderOut])
async def update_reminder(
    reminder_id: str,
    payload: ReminderUpdate,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    reminder = await db.get(Reminder, reminder_id)
    if not reminder:
        raise NotFoundException("提醒不存在")

    await _verify_member_in_family(reminder.member_id, current, db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(reminder, field, value)

    await db.commit()
    await db.refresh(reminder)
    return ResponseWrapper(data=ReminderOut.model_validate(reminder))


@router.delete("/{reminder_id}", response_model=ResponseWrapper[dict])
async def delete_reminder(
    reminder_id: str,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    reminder = await db.get(Reminder, reminder_id)
    if not reminder:
        raise NotFoundException("提醒不存在")

    await _verify_member_in_family(reminder.member_id, current, db)

    await db.delete(reminder)
    await db.commit()
    return ResponseWrapper(data={"deleted": True})
