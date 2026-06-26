from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.logging import get_logger
from app.core.milestone_data import get_milestones_for_age
from app.core.security import get_current_member, get_db
from app.models.growth_record import GrowthRecord
from app.models.member import Member
from app.schemas.common import ResponseWrapper
from app.schemas.growth import GrowthRecordCreate, GrowthRecordOut, MilestoneItem

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
    await _verify_member_in_family(member_id, current, db)
    stmt = select(GrowthRecord).where(GrowthRecord.member_id == member_id)
    if record_type:
        stmt = stmt.where(GrowthRecord.record_type == record_type)
    stmt = stmt.order_by(desc(GrowthRecord.recorded_at), desc(GrowthRecord.created_at))
    result = await db.execute(stmt)
    items = result.scalars().all()
    return ResponseWrapper(data=[GrowthRecordOut.model_validate(i) for i in items])


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
