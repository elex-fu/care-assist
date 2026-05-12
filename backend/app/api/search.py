from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.core.security import get_current_member, get_db
from app.core.exceptions import ForbiddenException
from app.models.member import Member
from app.models.indicator import IndicatorData
from app.models.report import Report
from app.models.health_event import HealthEvent
from app.models.reminder import Reminder
from app.models.hospital import HospitalEvent
from app.models.vaccine import VaccineRecord
from app.schemas.search import SearchResultItem
from app.schemas.common import ResponseWrapper

router = APIRouter(prefix="/search", tags=["搜索"])


async def _verify_member_in_family(member_id: str, current: Member, db: AsyncSession) -> Member:
    target = await db.get(Member, member_id)
    if not target:
        return None
    if target.family_id != current.family_id:
        raise ForbiddenException("无权限搜索其他家庭的成员")
    return target


@router.get("", response_model=ResponseWrapper[list[SearchResultItem]])
async def search(
    q: str = Query(..., min_length=1),
    member_id: str | None = Query(None),
    entity_types: str | None = Query(None, description="Comma-separated: indicator,report,health_event,reminder,hospital_event,vaccine"),
    limit: int = Query(20, ge=1, le=100),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    if member_id:
        await _verify_member_in_family(member_id, current, db)

    types = set()
    if entity_types:
        types = set(entity_types.split(","))
    else:
        types = {"indicator", "report", "health_event", "reminder", "hospital_event", "vaccine"}

    results = []
    search_lower = q.lower()

    # Search indicators
    if "indicator" in types:
        stmt = select(IndicatorData, Member.name.label("member_name")).join(
            Member, IndicatorData.member_id == Member.id
        ).where(Member.family_id == current.family_id)
        if member_id:
            stmt = stmt.where(IndicatorData.member_id == member_id)
        stmt = stmt.where(
            or_(
                IndicatorData.indicator_name.ilike(f"%{q}%"),
                IndicatorData.indicator_key.ilike(f"%{q}%"),
            )
        ).limit(limit)
        rows = (await db.execute(stmt)).all()
        for ind, mname in rows:
            results.append(SearchResultItem(
                entity_type="indicator",
                id=ind.id,
                member_id=ind.member_id,
                member_name=mname,
                title=f"{ind.indicator_name}: {ind.value} {ind.unit}",
                subtitle=f"状态: {ind.status}",
                record_date=ind.record_date,
                status=ind.status,
                data={"value": float(ind.value), "unit": ind.unit, "deviation": float(ind.deviation_percent) if ind.deviation_percent else None},
            ))

    # Search reports
    if "report" in types and len(results) < limit:
        stmt = select(Report, Member.name.label("member_name")).join(
            Member, Report.member_id == Member.id
        ).where(Member.family_id == current.family_id)
        if member_id:
            stmt = stmt.where(Report.member_id == member_id)
        stmt = stmt.where(
            or_(
                Report.type.ilike(f"%{q}%"),
                Report.hospital.ilike(f"%{q}%"),
                Report.department.ilike(f"%{q}%"),
            )
        ).limit(limit - len(results))
        rows = (await db.execute(stmt)).all()
        for rep, mname in rows:
            results.append(SearchResultItem(
                entity_type="report",
                id=rep.id,
                member_id=rep.member_id,
                member_name=mname,
                title=f"{rep.type}报告",
                subtitle=rep.hospital or None,
                record_date=rep.report_date,
                status=rep.ocr_status,
                data={"image_count": len(rep.images) if rep.images else 0},
            ))

    # Search health events
    if "health_event" in types and len(results) < limit:
        stmt = select(HealthEvent, Member.name.label("member_name")).join(
            Member, HealthEvent.member_id == Member.id
        ).where(Member.family_id == current.family_id)
        if member_id:
            stmt = stmt.where(HealthEvent.member_id == member_id)
        stmt = stmt.where(
            or_(
                HealthEvent.type.ilike(f"%{q}%"),
                HealthEvent.diagnosis.ilike(f"%{q}%"),
                HealthEvent.notes.ilike(f"%{q}%"),
                HealthEvent.hospital.ilike(f"%{q}%"),
            )
        ).limit(limit - len(results))
        rows = (await db.execute(stmt)).all()
        for evt, mname in rows:
            results.append(SearchResultItem(
                entity_type="health_event",
                id=evt.id,
                member_id=evt.member_id,
                member_name=mname,
                title=evt.type,
                subtitle=evt.diagnosis or evt.notes,
                record_date=evt.event_date,
                status=evt.status,
                data={"hospital": evt.hospital, "doctor": evt.doctor},
            ))

    # Search reminders
    if "reminder" in types and len(results) < limit:
        stmt = select(Reminder, Member.name.label("member_name")).join(
            Member, Reminder.member_id == Member.id
        ).where(Member.family_id == current.family_id)
        if member_id:
            stmt = stmt.where(Reminder.member_id == member_id)
        stmt = stmt.where(
            or_(
                Reminder.title.ilike(f"%{q}%"),
                Reminder.description.ilike(f"%{q}%"),
                Reminder.type.ilike(f"%{q}%"),
            )
        ).limit(limit - len(results))
        rows = (await db.execute(stmt)).all()
        for rem, mname in rows:
            results.append(SearchResultItem(
                entity_type="reminder",
                id=rem.id,
                member_id=rem.member_id,
                member_name=mname,
                title=rem.title,
                subtitle=rem.description,
                record_date=rem.scheduled_date,
                status=rem.status,
                data={"priority": rem.priority, "type": rem.type},
            ))

    # Search hospital events
    if "hospital_event" in types and len(results) < limit:
        stmt = select(HospitalEvent, Member.name.label("member_name")).join(
            Member, HospitalEvent.member_id == Member.id
        ).where(Member.family_id == current.family_id)
        if member_id:
            stmt = stmt.where(HospitalEvent.member_id == member_id)
        stmt = stmt.where(
            or_(
                HospitalEvent.hospital.ilike(f"%{q}%"),
                HospitalEvent.diagnosis.ilike(f"%{q}%"),
                HospitalEvent.department.ilike(f"%{q}%"),
            )
        ).limit(limit - len(results))
        rows = (await db.execute(stmt)).all()
        for hev, mname in rows:
            results.append(SearchResultItem(
                entity_type="hospital_event",
                id=hev.id,
                member_id=hev.member_id,
                member_name=mname,
                title=hev.hospital,
                subtitle=hev.diagnosis,
                record_date=hev.admission_date,
                status=hev.status,
                data={"department": hev.department, "doctor": hev.doctor},
            ))

    # Search vaccines
    if "vaccine" in types and len(results) < limit:
        stmt = select(VaccineRecord, Member.name.label("member_name")).join(
            Member, VaccineRecord.member_id == Member.id
        ).where(Member.family_id == current.family_id)
        if member_id:
            stmt = stmt.where(VaccineRecord.member_id == member_id)
        stmt = stmt.where(
            VaccineRecord.vaccine_name.ilike(f"%{q}%")
        ).limit(limit - len(results))
        rows = (await db.execute(stmt)).all()
        for vac, mname in rows:
            results.append(SearchResultItem(
                entity_type="vaccine",
                id=vac.id,
                member_id=vac.member_id,
                member_name=mname,
                title=vac.vaccine_name,
                subtitle=f"第{vac.dose}剂",
                record_date=vac.scheduled_date,
                status=vac.status,
                data={"dose": vac.dose, "actual_date": vac.actual_date.isoformat() if vac.actual_date else None},
            ))

    return ResponseWrapper(data=results[:limit])
