from datetime import date, datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_member, get_db
from app.core.exceptions import NotFoundException, ForbiddenException
from app.models.member import Member
from app.models.medication import Medication, MedicationLog
from app.schemas.medication import (
    MedicationCreate,
    MedicationUpdate,
    MedicationOut,
    MedicationLogOut,
    MedicationTakeRequest,
    MedicationWithLogsOut,
)
from app.schemas.common import ResponseWrapper

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
            logs=[MedicationLogOut.model_validate(l) for l in logs],
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
        existing.taken_at = datetime.now(timezone.utc)
        existing.notes = payload.notes
        await db.commit()
        await db.refresh(existing)
        return ResponseWrapper(data=MedicationLogOut.model_validate(existing))

    log = MedicationLog(
        medication_id=medication_id,
        member_id=medication.member_id,
        scheduled_date=payload.scheduled_date,
        scheduled_time=payload.scheduled_time,
        taken_at=datetime.now(timezone.utc),
        status="taken",
        notes=payload.notes,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return ResponseWrapper(data=MedicationLogOut.model_validate(log))
