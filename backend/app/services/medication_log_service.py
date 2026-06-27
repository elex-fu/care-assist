from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medication import Medication, MedicationLog


class MedicationLogService:
    """Service for idempotently generating MedicationLog entries."""

    @staticmethod
    async def generate_for_range(
        db: AsyncSession, member_id: str, start: date, end: date
    ) -> int:
        """Idempotently generate pending MedicationLog entries for active medications.

        Only creates entries that do not already exist for the same medication,
        scheduled_date and scheduled_time.
        """
        stmt = (
            select(Medication)
            .where(Medication.member_id == member_id)
            .where(Medication.status == "active")
            .where(Medication.start_date <= end)
            .where((Medication.end_date.is_(None)) | (Medication.end_date >= start))
        )
        result = await db.execute(stmt)
        meds = result.scalars().all()

        created = 0
        for med in meds:
            for offset in range((end - start).days + 1):
                scheduled_date = start + timedelta(days=offset)
                if scheduled_date < med.start_date:
                    continue
                if med.end_date and scheduled_date > med.end_date:
                    continue
                for slot in med.time_slots or []:
                    existing = await db.execute(
                        select(MedicationLog)
                        .where(MedicationLog.medication_id == med.id)
                        .where(MedicationLog.scheduled_date == scheduled_date)
                        .where(MedicationLog.scheduled_time == slot)
                    )
                    if existing.scalar_one_or_none():
                        continue
                    db.add(
                        MedicationLog(
                            medication_id=med.id,
                            member_id=member_id,
                            scheduled_date=scheduled_date,
                            scheduled_time=slot,
                            status="pending",
                        )
                    )
                    created += 1
        await db.commit()
        return created
