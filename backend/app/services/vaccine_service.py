"""Vaccine schedule helpers for auto-generating child records."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed import seed_vaccine_library
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


async def generate_child_vaccine_schedule(
    db: AsyncSession, member_id: str, birth_date: date | None
) -> list[VaccineRecord]:
    """Generate pending VaccineRecord rows from VaccineLibrary for a child member.

    The vaccine library is seeded if empty.  Scheduled dates are computed as
    birth_date + recommended_age_months and status defaults to "pending".
    """
    if not birth_date:
        return []

    await seed_vaccine_library(db)

    result = await db.execute(
        select(VaccineLibrary).order_by(VaccineLibrary.recommended_age_months)
    )
    entries = result.scalars().all()

    records: list[VaccineRecord] = []
    for entry in entries:
        records.append(
            VaccineRecord(
                member_id=member_id,
                vaccine_name=entry.name,
                dose=entry.dose_number,
                scheduled_date=add_months(birth_date, entry.recommended_age_months),
                status="pending",
                is_custom=False,
            )
        )

    if records:
        db.add_all(records)
        await db.commit()

    return records
