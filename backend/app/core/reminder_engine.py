from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medication import Medication, MedicationLog
from app.models.reminder import Reminder
from app.models.vaccine import VaccineRecord
from app.services.reminder_service import find_duplicate_reminder


class ReminderEngine:
    """Scan for missed medications, overdue vaccines and overdue reminders."""

    @staticmethod
    async def scan_missed_medications(
        db: AsyncSession, today: date | None = None
    ) -> int:
        today = today or date.today()
        stmt = (
            select(MedicationLog)
            .join(Medication)
            .where(Medication.status == "active")
            .where(MedicationLog.scheduled_date < today)
            .where(MedicationLog.status == "pending")
        )
        result = await db.execute(stmt)
        logs = result.scalars().all()

        for log in logs:
            log.status = "missed"
            title = f"漏服提醒：{log.medication.name}"
            description = f"{log.scheduled_date} {log.scheduled_time} 的剂量未打卡"
            duplicate = await find_duplicate_reminder(
                db,
                member_id=log.member_id,
                type="medication",
                scheduled_date=today,
                related_report_id=None,
                related_indicator=None,
            )
            if duplicate is None:
                db.add(
                    Reminder(
                        member_id=log.member_id,
                        type="medication",
                        title=title,
                        description=description,
                        scheduled_date=today,
                        status="pending",
                        priority="high",
                    )
                )
        await db.commit()
        return len(logs)

    @staticmethod
    async def scan_overdue_vaccines(
        db: AsyncSession, today: date | None = None
    ) -> int:
        today = today or date.today()
        stmt = (
            select(VaccineRecord)
            .where(VaccineRecord.status.in_(["pending", "upcoming"]))
            .where(VaccineRecord.scheduled_date < today)
        )
        result = await db.execute(stmt)
        records = result.scalars().all()

        for rec in records:
            rec.status = "overdue"
            title = f"疫苗逾期：{rec.vaccine_name} 第{rec.dose}针"
            description = f"原定于 {rec.scheduled_date} 接种，已逾期"
            duplicate = await find_duplicate_reminder(
                db,
                member_id=rec.member_id,
                type="vaccine",
                scheduled_date=today,
                related_report_id=None,
                related_indicator=None,
            )
            if duplicate is None:
                db.add(
                    Reminder(
                        member_id=rec.member_id,
                        type="vaccine",
                        title=title,
                        description=description,
                        scheduled_date=today,
                        status="pending",
                        priority="high",
                    )
                )
        await db.commit()
        return len(records)

    @staticmethod
    async def scan_overdue_reminders(
        db: AsyncSession, today: date | None = None
    ) -> int:
        today = today or date.today()
        stmt = (
            select(Reminder)
            .where(Reminder.status == "pending")
            .where(Reminder.scheduled_date < today)
        )
        result = await db.execute(stmt)
        reminders = result.scalars().all()

        for r in reminders:
            r.status = "overdue"
        await db.commit()
        return len(reminders)
