from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_member, get_db
from app.core.exceptions import NotFoundException, ForbiddenException
from app.models.member import Member
from app.models.hospital import HospitalEvent
from app.schemas.hospital import HospitalEventCreate, HospitalEventUpdate, HospitalEventOut
from app.schemas.common import ResponseWrapper

router = APIRouter(prefix="/hospital-events", tags=["住院管理"])


async def _verify_member_in_family(member_id: str, current: Member, db: AsyncSession) -> Member:
    target = await db.get(Member, member_id)
    if not target:
        raise NotFoundException("成员不存在")
    if target.family_id != current.family_id:
        raise ForbiddenException("无权限操作其他家庭的成员")
    return target


@router.post("", response_model=ResponseWrapper[HospitalEventOut])
async def create_hospital_event(
    payload: HospitalEventCreate,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    target = await _verify_member_in_family(payload.member_id, current, db)

    status = "discharged" if payload.discharge_date else "active"

    event = HospitalEvent(
        member_id=target.id,
        hospital=payload.hospital,
        department=payload.department,
        admission_date=payload.admission_date,
        discharge_date=payload.discharge_date,
        diagnosis=payload.diagnosis,
        doctor=payload.doctor,
        key_nodes=payload.key_nodes or [],
        watch_indicators=payload.watch_indicators or [],
        status=status,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return ResponseWrapper(data=HospitalEventOut.model_validate(event))


@router.get("", response_model=ResponseWrapper[list[HospitalEventOut]])
async def list_hospital_events(
    member_id: str = Query(...),
    status: Optional[str] = Query(None),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await _verify_member_in_family(member_id, current, db)

    stmt = select(HospitalEvent).where(HospitalEvent.member_id == member_id)
    if status:
        stmt = stmt.where(HospitalEvent.status == status)
    stmt = stmt.order_by(desc(HospitalEvent.admission_date))

    result = await db.execute(stmt)
    items = result.scalars().all()
    return ResponseWrapper(data=[HospitalEventOut.model_validate(i) for i in items])


@router.patch("/{event_id}", response_model=ResponseWrapper[HospitalEventOut])
async def update_hospital_event(
    event_id: str,
    payload: HospitalEventUpdate,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(HospitalEvent, event_id)
    if not event:
        raise NotFoundException("住院记录不存在")

    await _verify_member_in_family(event.member_id, current, db)

    update_data = payload.model_dump(exclude_unset=True)

    if "discharge_date" in update_data and update_data["discharge_date"]:
        update_data["status"] = "discharged"
    elif "status" not in update_data and event.discharge_date is None and payload.discharge_date is not None:
        update_data["status"] = "discharged"

    for field, value in update_data.items():
        setattr(event, field, value)

    await db.commit()
    await db.refresh(event)
    return ResponseWrapper(data=HospitalEventOut.model_validate(event))


@router.delete("/{event_id}", response_model=ResponseWrapper[dict])
async def delete_hospital_event(
    event_id: str,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(HospitalEvent, event_id)
    if not event:
        raise NotFoundException("住院记录不存在")

    await _verify_member_in_family(event.member_id, current, db)

    await db.delete(event)
    await db.commit()
    return ResponseWrapper(data={"deleted": True})
