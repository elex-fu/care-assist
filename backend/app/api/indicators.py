from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chronic_packages import (
    CHRONIC_PACKAGES,
    build_chronic_package,
    build_chronic_trend,
    list_chronic_packages,
)
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.indicator_engine import IndicatorEngine
from app.core.indicator_search import search_indicators
from app.core.logging import get_logger
from app.core.security import get_current_member, get_db
from app.models.indicator import IndicatorData
from app.models.member import Member
from app.schemas.batch import BatchIndicatorCreate
from app.schemas.chronic import (
    ChronicPackageListItem,
    ChronicPackageResponse,
    ChronicTrendOut,
)
from app.schemas.common import ResponseWrapper
from app.schemas.indicator import (
    IndicatorCompareOut,
    IndicatorCreate,
    IndicatorOut,
    IndicatorSeries,
    IndicatorSeriesPoint,
    IndicatorTrendOut,
    IndicatorTrendPoint,
)
from app.schemas.indicator_matrix import IndicatorMatrixResponse, MatrixCell
from app.schemas.indicator_metadata import IndicatorMetadata

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
    indicator_key: str | None = Query(None),
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


@router.get("/matrix", response_model=ResponseWrapper[IndicatorMatrixResponse])
async def get_indicator_matrix(
    member_id: str = Query(...),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    target = await _verify_member_in_family(member_id, current, db)

    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    result = await db.execute(
        select(IndicatorData)
        .where(
            IndicatorData.member_id == member_id,
            IndicatorData.record_date >= start_date,
            IndicatorData.record_date <= end_date,
        )
        .order_by(desc(IndicatorData.record_date), desc(IndicatorData.created_at))
    )
    records = result.scalars().all()

    # Build matrix
    dates = sorted({str(r.record_date) for r in records if start_date <= r.record_date <= end_date})
    keys = sorted({r.indicator_key for r in records})
    names = {r.indicator_key: r.indicator_name for r in records}
    units = {r.indicator_key: r.unit for r in records}

    cells: dict[str, dict[str, MatrixCell | None]] = {}
    for d in dates:
        cells[d] = dict.fromkeys(keys)

    for r in records:
        d = str(r.record_date)
        if d not in cells:
            continue
        # Keep latest record per date/key
        if cells[d][r.indicator_key] is None:
            cells[d][r.indicator_key] = MatrixCell(
                value=r.value,
                status=r.status,
                indicator_id=r.id,
            )

    matrix = IndicatorMatrixResponse(
        dates=dates,
        indicator_keys=keys,
        indicator_names=names,
        units=units,
        cells=cells,
    )
    return ResponseWrapper(data=matrix)


@router.get("/compare", response_model=ResponseWrapper[IndicatorCompareOut])
async def compare_indicators(
    member_id: str = Query(...),
    indicator_keys: list[str] = Query(default=[]),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """Compare multiple indicators over a date range."""
    target = await _verify_member_in_family(member_id, current, db)

    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=90)
    if not indicator_keys:
        return ResponseWrapper(data=IndicatorCompareOut(series=[]))

    stmt = (
        select(IndicatorData)
        .where(
            IndicatorData.member_id == member_id,
            IndicatorData.indicator_key.in_(indicator_keys),
            IndicatorData.record_date >= start_date,
            IndicatorData.record_date <= end_date,
        )
        .order_by(IndicatorData.record_date, IndicatorData.created_at)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    by_key: dict[str, list[IndicatorSeriesPoint]] = {k: [] for k in indicator_keys}
    names: dict[str, str] = {}
    units: dict[str, str] = {}
    for r in records:
        by_key[r.indicator_key].append(
            IndicatorSeriesPoint(
                value=float(r.value), record_date=r.record_date, status=r.status
            )
        )
        names[r.indicator_key] = r.indicator_name
        units[r.indicator_key] = r.unit

    series = [
        IndicatorSeries(
            indicator_key=k,
            indicator_name=names.get(k, k),
            unit=units.get(k, ""),
            points=by_key[k],
        )
        for k in indicator_keys
    ]
    return ResponseWrapper(data=IndicatorCompareOut(series=series))


@router.get("/metadata", response_model=ResponseWrapper[list[IndicatorMetadata]])
async def get_indicator_metadata(
    q: str = Query("", description="Search query for indicator name or alias"),
    limit: int = Query(10, ge=1, le=50),
    current: Member = Depends(get_current_member),
):
    """Search indicator metadata (name, unit, reference range, aliases)."""
    results = search_indicators(q, limit=limit)
    return ResponseWrapper(data=results)


@router.get("/chronic", response_model=ResponseWrapper[list[ChronicPackageListItem]])
async def list_chronic_packages_endpoint(
    current: Member = Depends(get_current_member),
):
    """List available chronic disease monitoring packages."""
    return ResponseWrapper(data=list_chronic_packages())


@router.get("/chronic/{package}", response_model=ResponseWrapper[ChronicPackageResponse])
async def get_chronic_package_endpoint(
    package: str,
    member_id: str = Query(...),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """Get chronic disease package details for a family member."""
    if package not in CHRONIC_PACKAGES:
        raise NotFoundException("套餐不存在")
    target = await _verify_member_in_family(member_id, current, db)
    data = await build_chronic_package(package, target, db)
    return ResponseWrapper(data=data)


@router.get("/chronic/{package}/trend", response_model=ResponseWrapper[ChronicTrendOut])
async def get_chronic_trend_endpoint(
    package: str,
    member_id: str = Query(...),
    days: int = Query(180, ge=7, le=730),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """Get multi-indicator trend data for a chronic disease package."""
    if package not in CHRONIC_PACKAGES:
        raise NotFoundException("套餐不存在")
    target = await _verify_member_in_family(member_id, current, db)
    data = await build_chronic_trend(package, target, db, days=days)
    return ResponseWrapper(data=data)
