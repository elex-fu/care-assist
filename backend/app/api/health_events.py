from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_member, get_db
from app.core.exceptions import NotFoundException, ForbiddenException
from app.models.member import Member
from app.models.health_event import HealthEvent
from app.schemas.health_event import HealthEventCreate, HealthEventUpdate, HealthEventOut
from app.schemas.common import ResponseWrapper

router = APIRouter(prefix="/health-events", tags=["健康时间轴"])


async def _verify_member_in_family(member_id: str, current: Member, db: AsyncSession) -> Member:
    target = await db.get(Member, member_id)
    if not target:
        raise NotFoundException("成员不存在")
    if target.family_id != current.family_id:
        raise ForbiddenException("无权限操作其他家庭的成员")
    return target


@router.post("", response_model=ResponseWrapper[HealthEventOut])
async def create_health_event(
    payload: HealthEventCreate,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    target = await _verify_member_in_family(payload.member_id, current, db)

    event = HealthEvent(
        member_id=target.id,
        type=payload.type,
        event_date=payload.event_date,
        event_time=payload.event_time,
        hospital=payload.hospital,
        department=payload.department,
        doctor=payload.doctor,
        diagnosis=payload.diagnosis,
        notes=payload.notes,
        report_id=payload.report_id,
        hospital_id=payload.hospital_id,
        status=payload.status,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return ResponseWrapper(data=HealthEventOut.model_validate(event))


@router.get("", response_model=ResponseWrapper[list[HealthEventOut]])
async def list_health_events(
    member_id: str = Query(...),
    event_type: Optional[str] = Query(None, alias="type"),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await _verify_member_in_family(member_id, current, db)

    stmt = select(HealthEvent).where(HealthEvent.member_id == member_id)
    if event_type:
        stmt = stmt.where(HealthEvent.type == event_type)
    stmt = stmt.order_by(desc(HealthEvent.event_date), desc(HealthEvent.created_at))

    result = await db.execute(stmt)
    items = result.scalars().all()
    return ResponseWrapper(data=[HealthEventOut.model_validate(i) for i in items])


@router.patch("/{event_id}", response_model=ResponseWrapper[HealthEventOut])
async def update_health_event(
    event_id: str,
    payload: HealthEventUpdate,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(HealthEvent, event_id)
    if not event:
        raise NotFoundException("健康事件不存在")

    await _verify_member_in_family(event.member_id, current, db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    await db.commit()
    await db.refresh(event)
    return ResponseWrapper(data=HealthEventOut.model_validate(event))


@router.delete("/{event_id}", response_model=ResponseWrapper[dict])
async def delete_health_event(
    event_id: str,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(HealthEvent, event_id)
    if not event:
        raise NotFoundException("健康事件不存在")

    await _verify_member_in_family(event.member_id, current, db)

    await db.delete(event)
    await db.commit()
    return ResponseWrapper(data={"deleted": True})
