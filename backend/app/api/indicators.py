from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_member, get_db
from app.core.exceptions import NotFoundException, ForbiddenException
from app.core.indicator_engine import IndicatorEngine
from app.core.logging import get_logger
from app.models.member import Member
from app.models.indicator import IndicatorData
from app.schemas.indicator import IndicatorCreate, IndicatorOut, IndicatorTrendOut, IndicatorTrendPoint
from app.schemas.batch import BatchIndicatorCreate
from app.schemas.common import ResponseWrapper

router = APIRouter(prefix="/indicators", tags=["指标中心"])
logger = get_logger("app.api.indicators")


def _calculate_age_months(birth_date: date | None) -> int | None:
    if not birth_date:
        return None
    today = date.today()
    months = (today.year - birth_date.year) * 12 + (today.month - birth_date.month)
    if today.day < birth_date.day:
        months -= 1
    return max(0, months)


async def _verify_member_in_family(member_id: str, current: Member, db: AsyncSession) -> Member:
    target = await db.get(Member, member_id)
    if not target:
        raise NotFoundException("成员不存在")
    if target.family_id != current.family_id:
        raise ForbiddenException("无权限操作其他家庭的成员")
    return target


@router.post("", response_model=ResponseWrapper[IndicatorOut])
async def create_indicator(
    payload: IndicatorCreate,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    target = await _verify_member_in_family(payload.member_id, current, db)

    age_months = _calculate_age_months(target.birth_date)

    status = IndicatorEngine.judge(payload.value, payload.indicator_key, age_months)
    deviation = IndicatorEngine.calculate_deviation(payload.value, payload.indicator_key, age_months)

    config = IndicatorEngine.THRESHOLDS.get(payload.indicator_key, {})
    threshold = config.get("threshold", {})
    if age_months and "age_groups" in config:
        for group in config["age_groups"]:
            if age_months <= group["max_age_months"]:
                threshold = group
                break

    indicator = IndicatorData(
        member_id=payload.member_id,
        indicator_key=payload.indicator_key,
        indicator_name=payload.indicator_name,
        value=Decimal(str(payload.value)),
        unit=payload.unit,
        lower_limit=Decimal(str(threshold.get("lower"))) if threshold.get("lower") is not None else None,
        upper_limit=Decimal(str(threshold.get("upper"))) if threshold.get("upper") is not None else None,
        status=status,
        deviation_percent=Decimal(str(round(deviation, 4))),
        record_date=payload.record_date,
        record_time=payload.record_time,
        source_report_id=payload.source_report_id,
        source_hospital_id=payload.source_hospital_id,
        source_batch_id=payload.source_batch_id,
    )
    db.add(indicator)
    await db.commit()
    await db.refresh(indicator)
    logger.info(
        f"Indicator created: id={indicator.id} member_id={payload.member_id} "
        f"key={payload.indicator_key} value={payload.value} status={status}"
    )
    return ResponseWrapper(data=IndicatorOut.model_validate(indicator))


@router.get("", response_model=ResponseWrapper[list[IndicatorOut]])
async def list_indicators(
    member_id: str = Query(...),
    indicator_key: Optional[str] = Query(None),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await _verify_member_in_family(member_id, current, db)

    stmt = select(IndicatorData).where(IndicatorData.member_id == member_id)
    if indicator_key:
        stmt = stmt.where(IndicatorData.indicator_key == indicator_key)
    stmt = stmt.order_by(desc(IndicatorData.record_date), desc(IndicatorData.created_at))

    result = await db.execute(stmt)
    items = result.scalars().all()
    return ResponseWrapper(data=[IndicatorOut.model_validate(i) for i in items])


@router.delete("/{indicator_id}", response_model=ResponseWrapper[dict])
async def delete_indicator(
    indicator_id: str,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    indicator = await db.get(IndicatorData, indicator_id)
    if not indicator:
        raise NotFoundException("指标记录不存在")

    await _verify_member_in_family(indicator.member_id, current, db)

    await db.delete(indicator)
    await db.commit()
    logger.info(f"Indicator deleted: id={indicator_id} member_id={indicator.member_id} key={indicator.indicator_key}")
    return ResponseWrapper(data={"deleted": True})


@router.post("/batch", response_model=ResponseWrapper[list[IndicatorOut]])
async def batch_create_indicators(
    payload: BatchIndicatorCreate,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    target = await _verify_member_in_family(payload.member_id, current, db)
    age_months = _calculate_age_months(target.birth_date)

    created = []
    for item in payload.items:
        status = IndicatorEngine.judge(item.value, item.indicator_key, age_months)
        deviation = IndicatorEngine.calculate_deviation(item.value, item.indicator_key, age_months)

        config = IndicatorEngine.THRESHOLDS.get(item.indicator_key, {})
        threshold = config.get("threshold", {})
        if age_months and "age_groups" in config:
            for group in config["age_groups"]:
                if age_months <= group["max_age_months"]:
                    threshold = group
                    break

        indicator = IndicatorData(
            member_id=payload.member_id,
            indicator_key=item.indicator_key,
            indicator_name=item.indicator_name,
            value=Decimal(str(item.value)),
            unit=item.unit,
            lower_limit=Decimal(str(threshold.get("lower"))) if threshold.get("lower") is not None else None,
            upper_limit=Decimal(str(threshold.get("upper"))) if threshold.get("upper") is not None else None,
            status=status,
            deviation_percent=Decimal(str(round(deviation, 4))),
            record_date=item.record_date,
            record_time=item.record_time,
            source_report_id=item.source_report_id,
            source_hospital_id=item.source_hospital_id,
            source_batch_id=item.source_batch_id,
        )
        db.add(indicator)
        created.append(indicator)

    await db.commit()
    for ind in created:
        await db.refresh(ind)
    logger.info(f"Batch indicators created: count={len(created)} member_id={payload.member_id}")
    return ResponseWrapper(data=[IndicatorOut.model_validate(i) for i in created])


@router.get("/trend", response_model=ResponseWrapper[IndicatorTrendOut])
async def get_indicator_trend(
    member_id: str = Query(...),
    indicator_key: str = Query(...),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    target = await _verify_member_in_family(member_id, current, db)

    stmt = (
        select(IndicatorData)
        .where(
            IndicatorData.member_id == member_id,
            IndicatorData.indicator_key == indicator_key,
        )
        .order_by(desc(IndicatorData.record_date), desc(IndicatorData.created_at))
        .limit(2)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    current_point = None
    previous_point = None
    trend = {"direction": "stable", "magnitude": "small", "evaluation": "stable"}

    if len(items) >= 1:
        i = items[0]
        current_point = IndicatorTrendPoint(
            value=float(i.value),
            record_date=i.record_date,
            record_time=i.record_time,
            status=i.status,
        )
    if len(items) >= 2:
        i = items[1]
        previous_point = IndicatorTrendPoint(
            value=float(i.value),
            record_date=i.record_date,
            record_time=i.record_time,
            status=i.status,
        )
        trend = IndicatorEngine.evaluate_trend(
            current_point.value, previous_point.value, indicator_key
        )

    config = IndicatorEngine.THRESHOLDS.get(indicator_key, {})
    return ResponseWrapper(data=IndicatorTrendOut(
        indicator_key=indicator_key,
        indicator_name=config.get("name", indicator_key),
        unit=config.get("unit", ""),
        current=current_point,
        previous=previous_point,
        trend=trend,
    ))
