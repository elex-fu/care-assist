from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_member, get_db
from app.core.exceptions import NotFoundException, ForbiddenException
from app.models.member import Member
from app.models.vaccine import VaccineRecord
from app.schemas.vaccine import VaccineRecordCreate, VaccineRecordUpdate, VaccineRecordOut
from app.schemas.common import ResponseWrapper

router = APIRouter(prefix="/vaccines", tags=["儿童疫苗"])


async def _verify_member_in_family(member_id: str, current: Member, db: AsyncSession) -> Member:
    target = await db.get(Member, member_id)
    if not target:
        raise NotFoundException("成员不存在")
    if target.family_id != current.family_id:
        raise ForbiddenException("无权限操作其他家庭的成员")
    return target


@router.post("", response_model=ResponseWrapper[VaccineRecordOut])
async def create_vaccine_record(
    payload: VaccineRecordCreate,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    target = await _verify_member_in_family(payload.member_id, current, db)

    record = VaccineRecord(
        member_id=target.id,
        vaccine_name=payload.vaccine_name,
        dose=payload.dose,
        scheduled_date=payload.scheduled_date,
        actual_date=payload.actual_date,
        status=payload.status,
        location=payload.location,
        batch_no=payload.batch_no,
        reaction=payload.reaction,
        is_custom=payload.is_custom,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return ResponseWrapper(data=VaccineRecordOut.model_validate(record))


@router.get("", response_model=ResponseWrapper[list[VaccineRecordOut]])
async def list_vaccine_records(
    member_id: str = Query(...),
    status: Optional[str] = Query(None),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await _verify_member_in_family(member_id, current, db)

    stmt = select(VaccineRecord).where(VaccineRecord.member_id == member_id)
    if status:
        stmt = stmt.where(VaccineRecord.status == status)
    stmt = stmt.order_by(desc(VaccineRecord.scheduled_date), desc(VaccineRecord.created_at))

    result = await db.execute(stmt)
    items = result.scalars().all()
    return ResponseWrapper(data=[VaccineRecordOut.model_validate(i) for i in items])


@router.patch("/{record_id}", response_model=ResponseWrapper[VaccineRecordOut])
async def update_vaccine_record(
    record_id: str,
    payload: VaccineRecordUpdate,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(VaccineRecord, record_id)
    if not record:
        raise NotFoundException("疫苗记录不存在")

    await _verify_member_in_family(record.member_id, current, db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)

    await db.commit()
    await db.refresh(record)
    return ResponseWrapper(data=VaccineRecordOut.model_validate(record))


@router.delete("/{record_id}", response_model=ResponseWrapper[dict])
async def delete_vaccine_record(
    record_id: str,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(VaccineRecord, record_id)
    if not record:
        raise NotFoundException("疫苗记录不存在")

    await _verify_member_in_family(record.member_id, current, db)

    await db.delete(record)
    await db.commit()
    return ResponseWrapper(data={"deleted": True})
