from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import get_current_member, get_db
from app.core.exceptions import NotFoundException, ForbiddenException, ConflictException
from app.core.permissions import PermissionChecker
from app.models.member import Member
from app.models.family import Family
from app.models.indicator import IndicatorData
from app.models.report import Report
from app.models.health_event import HealthEvent
from app.models.hospital import HospitalEvent
from app.models.vaccine import VaccineRecord
from app.models.reminder import Reminder
from app.schemas.member import (
    MemberUpdate,
    MemberOut,
    FamilyMembersOut,
    FamilyOut,
    SubscriptionUpdate,
)
from app.schemas.indicator import IndicatorOut
from app.schemas.common import ResponseWrapper
from sqlalchemy import select, desc

router = APIRouter(prefix="/members", tags=["成员管理"])


@router.get("/me", response_model=ResponseWrapper[MemberOut])
async def get_me(
    member: Member = Depends(get_current_member),
):
    return ResponseWrapper(data=MemberOut.model_validate(member))


@router.put("/me", response_model=ResponseWrapper[MemberOut])
async def update_me(
    update: MemberUpdate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(member, field, value)

    await db.commit()
    await db.refresh(member)
    return ResponseWrapper(data=MemberOut.model_validate(member))


@router.put("/me/subscription", response_model=ResponseWrapper[dict])
async def update_subscription(
    update: SubscriptionUpdate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    current = member.subscription_status or {}
    new_values = update.model_dump(exclude_unset=True)
    current.update(new_values)
    member.subscription_status = current

    await db.commit()
    await db.refresh(member)
    return ResponseWrapper(data={"subscription_status": member.subscription_status})


@router.post("", response_model=ResponseWrapper[MemberOut])
async def create_member(
    name: str,
    gender: str = "male",
    type: str = "adult",
    birth_date: str | None = None,
    blood_type: str | None = None,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    if not PermissionChecker.is_creator(current):
        raise ForbiddenException("仅家庭创建者可添加成员")

    import uuid
    from datetime import date as dt_date

    member = Member(
        id=str(uuid.uuid4()),
        family_id=current.family_id,
        name=name,
        gender=gender,
        type=type,
        birth_date=dt_date.fromisoformat(birth_date) if birth_date else None,
        blood_type=blood_type,
        role="member",
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return ResponseWrapper(data=MemberOut.model_validate(member))


@router.get("", response_model=ResponseWrapper[FamilyMembersOut])
async def list_family_members(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    family = await db.get(Family, member.family_id)
    if not family:
        raise NotFoundException("家庭不存在")

    result = await db.execute(select(Member).where(Member.family_id == family.id))
    members = result.scalars().all()

    return ResponseWrapper(
        data=FamilyMembersOut(
            family=FamilyOut.model_validate(family),
            members=[MemberOut.model_validate(m) for m in members],
        )
    )


@router.post("/family", response_model=ResponseWrapper[MemberOut])
async def create_family(
    creator_name: str,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """Create a new family and set current member as creator.
    Only for members not already in a family (rare edge case)."""
    import secrets
    import uuid

    if member.family_id:
        raise ConflictException("您已加入家庭，无法重复创建")

    family = Family(
        id=str(uuid.uuid4()),
        name=f"{creator_name}的家庭",
        invite_code=secrets.token_urlsafe(8)[:6].upper(),
    )
    db.add(family)
    await db.flush()

    member.family_id = family.id
    member.role = "creator"
    member.name = creator_name
    family.admin_id = member.id

    await db.commit()
    await db.refresh(member)
    return ResponseWrapper(data=MemberOut.model_validate(member))


@router.post("/invite", response_model=ResponseWrapper[dict])
async def generate_invite(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    if not PermissionChecker.is_creator(member):
        raise ForbiddenException("仅家庭创建者可生成邀请链接")

    from app.core.security import create_jwt

    token = create_jwt(
        str(member.id),
        token_type="invite",
        extra_claims={"family_id": member.family_id},
    )

    return ResponseWrapper(
        data={
            "invite_link": f"/join?token={token}",
            "expires_at": "7d",
        }
    )


@router.post("/join", response_model=ResponseWrapper[MemberOut])
async def join_family(
    token: str,
    name: str,
    db: AsyncSession = Depends(get_db),
):
    from app.core.security import decode_jwt

    try:
        payload = decode_jwt(token)
    except Exception as exc:
        raise ForbiddenException("无效的邀请链接") from exc

    if payload.get("type") != "invite":
        raise ForbiddenException("无效的邀请链接")

    family_id = payload.get("family_id")
    if not family_id:
        raise ForbiddenException("无效的邀请链接")

    family = await db.get(Family, family_id)
    if not family:
        raise NotFoundException("家庭不存在")

    import uuid

    new_member = Member(
        id=str(uuid.uuid4()),
        family_id=family_id,
        name=name,
        gender="male",
        role="member",
    )
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)

    return ResponseWrapper(data=MemberOut.model_validate(new_member))


@router.get("/{member_id}/export", response_model=ResponseWrapper[dict])
async def export_member_health(
    member_id: str,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(Member, member_id)
    if not target:
        raise NotFoundException("成员不存在")
    if target.family_id != current.family_id:
        raise ForbiddenException("无权限导出其他家庭成员的数据")

    # Indicators
    stmt = select(IndicatorData).where(IndicatorData.member_id == member_id).order_by(desc(IndicatorData.record_date))
    result = await db.execute(stmt)
    indicators = result.scalars().all()

    # Reports
    stmt = select(Report).where(Report.member_id == member_id).order_by(desc(Report.report_date))
    result = await db.execute(stmt)
    reports = result.scalars().all()

    # Health events
    stmt = select(HealthEvent).where(HealthEvent.member_id == member_id).order_by(desc(HealthEvent.event_date))
    result = await db.execute(stmt)
    events = result.scalars().all()

    # Hospital events
    stmt = select(HospitalEvent).where(HospitalEvent.member_id == member_id).order_by(desc(HospitalEvent.admission_date))
    result = await db.execute(stmt)
    hospitals = result.scalars().all()

    # Vaccines
    stmt = select(VaccineRecord).where(VaccineRecord.member_id == member_id).order_by(desc(VaccineRecord.scheduled_date))
    result = await db.execute(stmt)
    vaccines = result.scalars().all()

    # Reminders
    stmt = select(Reminder).where(Reminder.member_id == member_id).order_by(desc(Reminder.scheduled_date))
    result = await db.execute(stmt)
    reminders = result.scalars().all()

    return ResponseWrapper(
        data={
            "member": MemberOut.model_validate(target).model_dump(),
            "indicators": [IndicatorOut.model_validate(i).model_dump() for i in indicators],
            "reports": [{"id": r.id, "type": r.type, "hospital": r.hospital, "report_date": r.report_date.isoformat() if r.report_date else None, "ocr_status": r.ocr_status} for r in reports],
            "health_events": [{"id": e.id, "type": e.type, "event_date": e.event_date.isoformat() if e.event_date else None, "diagnosis": e.diagnosis, "status": e.status} for e in events],
            "hospital_events": [{"id": h.id, "hospital": h.hospital, "admission_date": h.admission_date.isoformat() if h.admission_date else None, "discharge_date": h.discharge_date.isoformat() if h.discharge_date else None, "diagnosis": h.diagnosis, "status": h.status} for h in hospitals],
            "vaccines": [{"id": v.id, "vaccine_name": v.vaccine_name, "dose": v.dose, "scheduled_date": v.scheduled_date.isoformat() if v.scheduled_date else None, "status": v.status} for v in vaccines],
            "reminders": [{"id": r.id, "title": r.title, "type": r.type, "scheduled_date": r.scheduled_date.isoformat() if r.scheduled_date else None, "status": r.status} for r in reminders],
        }
    )


@router.delete("/{member_id}", response_model=ResponseWrapper[dict])
async def delete_member(
    member_id: str,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    if not PermissionChecker.is_creator(current):
        raise ForbiddenException("仅家庭创建者可删除成员")

    if current.id == member_id:
        raise ForbiddenException("无法删除自己")

    target = await db.get(Member, member_id)
    if not target:
        raise NotFoundException("成员不存在")

    if target.family_id != current.family_id:
        raise ForbiddenException("无法删除其他家庭的成员")

    await db.delete(target)
    await db.commit()

    return ResponseWrapper(data={"deleted": True})
