from calendar import monthrange
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.security import get_current_member, get_db
from app.models.medication import Medication, MedicationLog
from app.models.member import Member
from app.schemas.common import ResponseWrapper
from app.schemas.medication import (
    MedicationCalendarDay,
    MedicationCalendarOut,
    MedicationCreate,
    MedicationLogOut,
    MedicationLogUpdate,
    MedicationOut,
    MedicationTakeRequest,
    MedicationUpdate,
    MedicationWithLogsOut,
)
from app.services.medication_log_service import MedicationLogService

router = APIRouter(prefix="/medications", tags=["用药管理"])


async def _verify_member_in_family(member_id: str, current: Member, db: AsyncSession) -> Member:
    target = await db.get(Member, member_id)
    if not target:
        raise NotFoundException("成员不存在")
    if target.family_id != current.family_id:
        raise ForbiddenException("无权限操作其他家庭的成员")
    return target


@router.post("", response_model=ResponseWrapper[MedicationOut])
async def create_medication(
    payload: MedicationCreate,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    target = await _verify_member_in_family(payload.member_id, current, db)

    medication = Medication(
        member_id=target.id,
        name=payload.name,
        dosage=payload.dosage,
        frequency=payload.frequency,
        time_slots=payload.time_slots,
        start_date=payload.start_date,
        end_date=payload.end_date,
        notes=payload.notes,
        status=payload.status,
    )
    db.add(medication)
    await db.commit()
    await db.refresh(medication)
    return ResponseWrapper(data=MedicationOut.model_validate(medication))


@router.get("", response_model=ResponseWrapper[list[MedicationOut]])
async def list_medications(
    member_id: str = Query(...),
    status: str | None = Query(None),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await _verify_member_in_family(member_id, current, db)

    stmt = select(Medication).where(Medication.member_id == member_id)
    if status:
        stmt = stmt.where(Medication.status == status)
    stmt = stmt.order_by(desc(Medication.created_at))

    result = await db.execute(stmt)
    items = result.scalars().all()
    return ResponseWrapper(data=[MedicationOut.model_validate(i) for i in items])


@router.get("/logs", response_model=ResponseWrapper[list[MedicationLogOut]])
async def list_medication_logs(
    member_id: str = Query(...),
    date: date = Query(...),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """Return all medication log entries for a specific member and date."""
    await _verify_member_in_family(member_id, current, db)

    stmt = (
        select(MedicationLog)
        .where(MedicationLog.member_id == member_id)
        .where(MedicationLog.scheduled_date == date)
        .order_by(MedicationLog.scheduled_time)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()
    data = []
    for log in logs:
        out = MedicationLogOut.model_validate(log)
        if log.medication:
            out.medication_name = log.medication.name
        data.append(out)
    return ResponseWrapper(data=data)


@router.patch("/logs/{log_id}", response_model=ResponseWrapper[MedicationLogOut])
async def update_medication_log(
    log_id: str,
    payload: MedicationLogUpdate,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """Update a medication log status (taken / missed / skipped / pending)."""
    log = await db.get(MedicationLog, log_id)
    if not log:
        raise NotFoundException("用药记录不存在")

    await _verify_member_in_family(log.member_id, current, db)

    update_data = payload.model_dump(exclude_unset=True)
    if update_data.get("status") == "taken" and not log.taken_at:
        log.taken_at = datetime.now(UTC)
    elif update_data.get("status") != "taken":
        log.taken_at = None

    for field, value in update_data.items():
        setattr(log, field, value)

    await db.commit()
    await db.refresh(log)
    return ResponseWrapper(data=MedicationLogOut.model_validate(log))


@router.get("/calendar", response_model=ResponseWrapper[MedicationCalendarOut])
async def get_medication_calendar(
    member_id: str = Query(...),
    year_month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """Return daily medication adherence for a given month."""
    target = await _verify_member_in_family(member_id, current, db)

    year, month = map(int, year_month.split("-"))
    _, last_day = monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, last_day)

    # Ensure pending logs exist for the requested month
    await MedicationLogService.generate_for_range(db, target.id, start, end)

    stmt = (
        select(MedicationLog)
        .where(MedicationLog.member_id == target.id)
        .where(MedicationLog.scheduled_date >= start)
        .where(MedicationLog.scheduled_date <= end)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    by_date: dict[date, list[MedicationLog]] = {}
    for log in logs:
        by_date.setdefault(log.scheduled_date, []).append(log)

    days = []
    for d in range(1, last_day + 1):
        cur = date(year, month, d)
        day_logs = by_date.get(cur, [])
        scheduled = len(day_logs)
        taken = sum(1 for log in day_logs if log.status == "taken")
        missed = sum(1 for log in day_logs if log.status == "missed")
        skipped = sum(1 for log in day_logs if log.status == "skipped")
        status = "none"
        if scheduled:
            if taken == scheduled:
                status = "complete"
            elif missed > 0:
                status = "missed" if (missed + skipped) == scheduled else "partial"
            elif skipped == scheduled:
                status = "skipped"
            else:
                status = "partial"
        days.append(
            MedicationCalendarDay(
                date=cur,
                scheduled_count=scheduled,
                taken_count=taken,
                missed_count=missed,
                skipped_count=skipped,
                status=status,
            )
        )

    return ResponseWrapper(data=MedicationCalendarOut(year=year, month=month, days=days))


@router.get("/{medication_id}", response_model=ResponseWrapper[MedicationWithLogsOut])
async def get_medication(
    medication_id: str,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    medication = await db.get(Medication, medication_id)
    if not medication:
        raise NotFoundException("用药记录不存在")

    await _verify_member_in_family(medication.member_id, current, db)

    # Default to last 7 days if no dates provided
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=6)

    stmt = (
        select(MedicationLog)
        .where(MedicationLog.medication_id == medication_id)
        .where(MedicationLog.scheduled_date >= start_date)
        .where(MedicationLog.scheduled_date <= end_date)
        .order_by(MedicationLog.scheduled_date, MedicationLog.scheduled_time)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    # Calculate adherence rate
    total = len(logs)
    taken = sum(1 for log in logs if log.status == "taken")
    adherence_rate = (taken / total * 100) if total > 0 else 0.0

    return ResponseWrapper(
        data=MedicationWithLogsOut(
            medication=MedicationOut.model_validate(medication),
            logs=[MedicationLogOut.model_validate(log) for log in logs],
            adherence_rate=round(adherence_rate, 1),
        )
    )


@router.patch("/{medication_id}", response_model=ResponseWrapper[MedicationOut])
async def update_medication(
    medication_id: str,
    payload: MedicationUpdate,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    medication = await db.get(Medication, medication_id)
    if not medication:
        raise NotFoundException("用药记录不存在")

    await _verify_member_in_family(medication.member_id, current, db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(medication, field, value)

    await db.commit()
    await db.refresh(medication)
    return ResponseWrapper(data=MedicationOut.model_validate(medication))


@router.delete("/{medication_id}", response_model=ResponseWrapper[dict])
async def delete_medication(
    medication_id: str,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    medication = await db.get(Medication, medication_id)
    if not medication:
        raise NotFoundException("用药记录不存在")

    await _verify_member_in_family(medication.member_id, current, db)

    await db.delete(medication)
    await db.commit()
    return ResponseWrapper(data={"deleted": True})


@router.post("/{medication_id}/take", response_model=ResponseWrapper[MedicationLogOut])
async def take_medication(
    medication_id: str,
    payload: MedicationTakeRequest,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    medication = await db.get(Medication, medication_id)
    if not medication:
        raise NotFoundException("用药记录不存在")

    await _verify_member_in_family(medication.member_id, current, db)

    # Check if log already exists for this scheduled slot
    stmt = (
        select(MedicationLog)
        .where(MedicationLog.medication_id == medication_id)
        .where(MedicationLog.scheduled_date == payload.scheduled_date)
        .where(MedicationLog.scheduled_time == payload.scheduled_time)
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        existing.status = "taken"
        existing.taken_at = datetime.now(UTC)
        existing.notes = payload.notes
        await db.commit()
        await db.refresh(existing)
        return ResponseWrapper(data=MedicationLogOut.model_validate(existing))

    log = MedicationLog(
        medication_id=medication_id,
        member_id=medication.member_id,
        scheduled_date=payload.scheduled_date,
        scheduled_time=payload.scheduled_time,
        taken_at=datetime.now(UTC),
        status="taken",
        notes=payload.notes,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return ResponseWrapper(data=MedicationLogOut.model_validate(log))
