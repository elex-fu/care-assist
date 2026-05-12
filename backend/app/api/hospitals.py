from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_member, get_db
from app.core.exceptions import NotFoundException, ForbiddenException
from app.core.indicator_engine import IndicatorEngine
from app.models.member import Member
from app.models.hospital import HospitalEvent
from app.schemas.hospital import HospitalEventCreate, HospitalEventUpdate, HospitalEventOut
from app.schemas.indicator import IndicatorOut
from app.schemas.common import ResponseWrapper
from app.models.indicator import IndicatorData

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


@router.get("/{event_id}/watch", response_model=ResponseWrapper[list[dict]])
async def get_watch_indicators(
    event_id: str,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(HospitalEvent, event_id)
    if not event:
        raise NotFoundException("住院记录不存在")

    await _verify_member_in_family(event.member_id, current, db)

    watch_keys = event.watch_indicators or []
    if not watch_keys:
        return ResponseWrapper(data=[])

    results = []
    for key in watch_keys:
        stmt = (
            select(IndicatorData)
            .where(
                IndicatorData.member_id == event.member_id,
                IndicatorData.indicator_key == key,
            )
            .order_by(desc(IndicatorData.record_date), desc(IndicatorData.created_at))
            .limit(2)
        )
        res = await db.execute(stmt)
        items = res.scalars().all()

        if not items:
            continue

        latest = items[0]
        previous = items[1] if len(items) >= 2 else None

        change = None
        change_percent = None
        if previous:
            change = round(float(latest.value) - float(previous.value), 4)
            if float(previous.value) != 0:
                change_percent = round(change / float(previous.value) * 100, 2)

        results.append({
            "indicator_key": key,
            "indicator_name": latest.indicator_name,
            "value": float(latest.value),
            "unit": latest.unit,
            "status": latest.status,
            "lower_limit": float(latest.lower_limit) if latest.lower_limit is not None else None,
            "upper_limit": float(latest.upper_limit) if latest.upper_limit is not None else None,
            "record_date": latest.record_date.isoformat(),
            "record_time": latest.record_time.isoformat() if latest.record_time else None,
            "previous_value": float(previous.value) if previous else None,
            "change": change,
            "change_percent": change_percent,
        })

    # Sort: abnormal first
    status_order = {"critical": 0, "high": 1, "low": 2, "normal": 3}
    results.sort(key=lambda x: status_order.get(x["status"], 4))

    return ResponseWrapper(data=results)


@router.get("/{event_id}/compare", response_model=ResponseWrapper[dict])
async def compare_hospital_indicators(
    event_id: str,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(HospitalEvent, event_id)
    if not event:
        raise NotFoundException("住院记录不存在")

    await _verify_member_in_family(event.member_id, current, db)

    from datetime import timedelta

    today = date.today()
    yesterday = today - timedelta(days=1)

    # Get today's indicators
    stmt_today = (
        select(IndicatorData)
        .where(
            IndicatorData.member_id == event.member_id,
            IndicatorData.record_date == today,
        )
        .order_by(desc(IndicatorData.created_at))
    )
    res_today = await db.execute(stmt_today)
    today_items = {i.indicator_key: i for i in res_today.scalars().all()}

    # Get yesterday's indicators
    stmt_yesterday = (
        select(IndicatorData)
        .where(
            IndicatorData.member_id == event.member_id,
            IndicatorData.record_date == yesterday,
        )
        .order_by(desc(IndicatorData.created_at))
    )
    res_yesterday = await db.execute(stmt_yesterday)
    yesterday_items = {i.indicator_key: i for i in res_yesterday.scalars().all()}

    # Compare common keys
    comparison = []
    for key in set(today_items.keys()) & set(yesterday_items.keys()):
        t = today_items[key]
        y = yesterday_items[key]
        change = round(float(t.value) - float(y.value), 4)
        change_pct = round(change / float(y.value) * 100, 2) if float(y.value) != 0 else 0.0

        # Use IndicatorEngine for consistent trend evaluation
        trend = IndicatorEngine.evaluate_trend(float(t.value), float(y.value), key)
        evaluation = trend["evaluation"]

        comparison.append({
            "indicator_key": key,
            "indicator_name": t.indicator_name,
            "today": float(t.value),
            "yesterday": float(y.value),
            "change": change,
            "change_percent": change_pct,
            "evaluation": evaluation,
            "unit": t.unit,
            "today_status": t.status,
            "yesterday_status": y.status,
        })

    # Sort: worsening/concerning first, then by abs change
    comparison.sort(key=lambda x: (
        0 if x["evaluation"] in ["worsening", "concerning"] else 1,
        abs(x["change_percent"]),
    ), reverse=True)

    improved = sum(1 for c in comparison if c["evaluation"] == "improving")
    worsened = sum(1 for c in comparison if c["evaluation"] in ["worsening", "concerning"])
    stable = sum(1 for c in comparison if c["evaluation"] == "stable")

    return ResponseWrapper(data={
        "event_id": event_id,
        "today": today.isoformat(),
        "yesterday": yesterday.isoformat(),
        "total": len(comparison),
        "improved": improved,
        "worsened": worsened,
        "stable": stable,
        "indicators": comparison,
    })
