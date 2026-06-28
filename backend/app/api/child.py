from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.logging import get_logger
from app.core.milestone_data import get_milestones_for_age
from app.core.security import get_current_member, get_db
from app.core.who_percentiles import (
    assess_growth,
    get_percentile_curve,
)
from app.models.growth_record import GrowthRecord
from app.models.member import Member
from app.schemas.common import ResponseWrapper
from app.schemas.growth import (
    GrowthChartOut,
    GrowthChartPoint,
    GrowthRecordCreate,
    GrowthRecordOut,
    MilestoneItem,
)

router = APIRouter(prefix="/child", tags=["儿童成长"])
logger = get_logger("app.api.child")


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


def _age_at_date(birth_date: date | None, recorded_at: date) -> int | None:
    if not birth_date:
        return None
    months = (recorded_at.year - birth_date.year) * 12 + (recorded_at.month - birth_date.month)
    if recorded_at.day < birth_date.day:
        months -= 1
    return max(0, months)


def _enrich_growth_record(record: GrowthRecord, member: Member) -> GrowthRecordOut:
    age_months = _age_at_date(member.birth_date, record.recorded_at)
    out = GrowthRecordOut.model_validate(record)
    out.age_months = age_months
    if age_months is not None and age_months <= 60 and member.gender in ("male", "female"):
        assessment = assess_growth(record.record_type, member.gender, age_months, record.value)
        out.percentile = assessment.percentile
        out.z_score = assessment.z_score
        out.status = assessment.status
        out.assessment_label = assessment.label
    return out


@router.post("/growth", response_model=ResponseWrapper[GrowthRecordOut])
async def create_growth_record(
    payload: GrowthRecordCreate,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
) -> ResponseWrapper[GrowthRecordOut]:
    await _verify_member_in_family(payload.member_id, current, db)
    record = GrowthRecord(
        member_id=payload.member_id,
        record_type=payload.record_type,
        value=payload.value,
        unit=payload.unit,
        recorded_at=payload.recorded_at,
        note=payload.note,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    logger.info(
        f"Growth record created: id={record.id} member_id={payload.member_id} "
        f"type={payload.record_type} value={payload.value}"
    )
    return ResponseWrapper(data=GrowthRecordOut.model_validate(record))


@router.get("/growth", response_model=ResponseWrapper[list[GrowthRecordOut]])
async def list_growth_records(
    member_id: str = Query(...),
    record_type: str | None = Query(None),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
) -> ResponseWrapper[list[GrowthRecordOut]]:
    target = await _verify_member_in_family(member_id, current, db)
    stmt = select(GrowthRecord).where(GrowthRecord.member_id == member_id)
    if record_type:
        stmt = stmt.where(GrowthRecord.record_type == record_type)
    stmt = stmt.order_by(desc(GrowthRecord.recorded_at), desc(GrowthRecord.created_at))
    result = await db.execute(stmt)
    items = result.scalars().all()
    return ResponseWrapper(data=[_enrich_growth_record(i, target) for i in items])


@router.get("/growth/chart", response_model=ResponseWrapper[GrowthChartOut])
async def get_growth_chart(
    member_id: str = Query(...),
    record_type: str = Query(...),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
) -> ResponseWrapper[GrowthChartOut]:
    target = await _verify_member_in_family(member_id, current, db)
    stmt = (
        select(GrowthRecord)
        .where(GrowthRecord.member_id == member_id)
        .where(GrowthRecord.record_type == record_type)
        .order_by(GrowthRecord.recorded_at)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    records = [_enrich_growth_record(i, target) for i in items]
    age_months_values = [r.age_months for r in records if r.age_months is not None]
    min_age = min(age_months_values) if age_months_values else 0
    max_age = max(age_months_values) if age_months_values else 60
    # Extend the curve a little beyond actual data for context.
    start_age = max(0, min_age - 1)
    end_age = min(60, max_age + 3)

    sex = target.gender if target.gender in ("male", "female") else "male"
    curve = get_percentile_curve(record_type, sex, age_range_months=(start_age, end_age), step=1)
    percentile_curve = [GrowthChartPoint(**point) for point in curve]

    return ResponseWrapper(
        data=GrowthChartOut(
            record_type=record_type,
            unit=records[0].unit if records else "",
            records=records,
            percentile_curve=percentile_curve,
        )
    )


@router.delete("/growth/{record_id}", response_model=ResponseWrapper[dict[str, bool]])
async def delete_growth_record(
    record_id: str,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
) -> ResponseWrapper[dict[str, bool]]:
    record = await db.get(GrowthRecord, record_id)
    if not record:
        raise NotFoundException("成长记录不存在")
    await _verify_member_in_family(record.member_id, current, db)
    await db.delete(record)
    await db.commit()
    logger.info(f"Growth record deleted: id={record_id} member_id={record.member_id}")
    return ResponseWrapper(data={"deleted": True})


@router.get("/milestones", response_model=ResponseWrapper[list[MilestoneItem]])
async def list_milestones(
    member_id: str = Query(...),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
) -> ResponseWrapper[list[MilestoneItem]]:
    target = await _verify_member_in_family(member_id, current, db)
    age_months = _calculate_age_months(target.birth_date)
    milestones = get_milestones_for_age(age_months)
    return ResponseWrapper(data=milestones)
