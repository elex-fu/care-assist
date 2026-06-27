"""Vaccine schedule generation from the standard vaccine library."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.member import Member
from app.models.vaccine import VaccineRecord
from app.models.vaccine_library import VaccineLibrary


def add_months(d: date, months: int) -> date:
    """Add months to a date, clamping day to the end of the resulting month."""
    year = d.year + (d.month + months - 1) // 12
    month = (d.month + months - 1) % 12 + 1
    leap = (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
    days_in_month = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    day = min(d.day, days_in_month)
    return date(year, month, day)


async def generate_vaccine_schedule(db: AsyncSession, member: Member) -> list[VaccineRecord]:
    """Generate VaccineRecord entries from VaccineLibrary for a member.

    Idempotent: skips doses that already exist for the member.
    """
    if not member.birth_date:
        return []

    lib_result = await db.execute(
        select(VaccineLibrary).order_by(VaccineLibrary.recommended_age_months)
    )
    entries = lib_result.scalars().all()

    existing_result = await db.execute(
        select(VaccineRecord.vaccine_name, VaccineRecord.dose).where(
            VaccineRecord.member_id == member.id
        )
    )
    existing_keys = {(name, dose) for name, dose in existing_result.all()}

    today = date.today()
    records: list[VaccineRecord] = []
    for entry in entries:
        key = (entry.name, entry.dose_number)
        if key in existing_keys:
            continue

        scheduled = add_months(member.birth_date, entry.recommended_age_months)
        if scheduled < today:
            status = "overdue"
        elif scheduled > today:
            status = "upcoming"
        else:
            status = "pending"

        records.append(
            VaccineRecord(
                member_id=member.id,
                vaccine_name=entry.name,
                dose=entry.dose_number,
                scheduled_date=scheduled,
                status=status,
                is_custom=False,
            )
        )

    if records:
        db.add_all(records)
        await db.commit()

    return records
