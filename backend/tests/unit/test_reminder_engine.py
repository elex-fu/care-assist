from datetime import date

import pytest

from app.core.reminder_engine import ReminderEngine
from app.models.medication import Medication, MedicationLog
from app.models.reminder import Reminder
from app.models.vaccine import VaccineRecord


@pytest.mark.asyncio
async def test_scan_missed_medications(db, test_member):
    med = Medication(
        member_id=test_member.id,
        name="测试药",
        dosage="1片",
        frequency="daily",
        time_slots=["08:00"],
        start_date=date(2020, 1, 1),
        status="active",
    )
    db.add(med)
    await db.flush()

    log = MedicationLog(
        medication_id=med.id,
        member_id=test_member.id,
        scheduled_date=date(2020, 1, 1),
        scheduled_time="08:00",
        status="pending",
    )
    db.add(log)
    await db.commit()

    count = await ReminderEngine.scan_missed_medications(db, today=date(2020, 1, 2))
    assert count >= 1
    assert log.status == "missed"

    reminders = await db.execute(
        Reminder.__table__.select().where(Reminder.member_id == test_member.id)
    )
    assert len(reminders.scalars().all()) >= 1


@pytest.mark.asyncio
async def test_scan_missed_medications_deduplicates(db, test_member):
    med = Medication(
        member_id=test_member.id,
        name="测试药",
        dosage="1片",
        frequency="daily",
        time_slots=["08:00"],
        start_date=date(2020, 1, 1),
        status="active",
    )
    db.add(med)
    await db.flush()

    log = MedicationLog(
        medication_id=med.id,
        member_id=test_member.id,
        scheduled_date=date(2020, 1, 1),
        scheduled_time="08:00",
        status="pending",
    )
    db.add(log)
    await db.commit()

    await ReminderEngine.scan_missed_medications(db, today=date(2020, 1, 2))
    first_count = len(
        (await db.execute(Reminder.__table__.select().where(Reminder.member_id == test_member.id)))
        .scalars()
        .all()
    )

    await ReminderEngine.scan_missed_medications(db, today=date(2020, 1, 2))
    second_count = len(
        (await db.execute(Reminder.__table__.select().where(Reminder.member_id == test_member.id)))
        .scalars()
        .all()
    )

    assert first_count == second_count


@pytest.mark.asyncio
async def test_scan_overdue_vaccines(db, test_member):
    rec = VaccineRecord(
        member_id=test_member.id,
        vaccine_name="测试疫苗",
        dose=1,
        scheduled_date=date(2020, 1, 1),
        status="pending",
    )
    db.add(rec)
    await db.commit()

    count = await ReminderEngine.scan_overdue_vaccines(db, today=date(2020, 1, 2))
    assert count == 1
    assert rec.status == "overdue"


@pytest.mark.asyncio
async def test_scan_overdue_vaccines_deduplicates(db, test_member):
    rec = VaccineRecord(
        member_id=test_member.id,
        vaccine_name="测试疫苗",
        dose=1,
        scheduled_date=date(2020, 1, 1),
        status="pending",
    )
    db.add(rec)
    await db.commit()

    await ReminderEngine.scan_overdue_vaccines(db, today=date(2020, 1, 2))
    first_count = len(
        (await db.execute(Reminder.__table__.select().where(Reminder.member_id == test_member.id)))
        .scalars()
        .all()
    )

    await ReminderEngine.scan_overdue_vaccines(db, today=date(2020, 1, 2))
    second_count = len(
        (await db.execute(Reminder.__table__.select().where(Reminder.member_id == test_member.id)))
        .scalars()
        .all()
    )

    assert first_count == second_count


@pytest.mark.asyncio
async def test_scan_overdue_reminders(db, test_member):
    reminder = Reminder(
        member_id=test_member.id,
        type="checkup",
        title="复查",
        description="",
        scheduled_date=date(2020, 1, 1),
        status="pending",
        priority="normal",
    )
    db.add(reminder)
    await db.commit()

    count = await ReminderEngine.scan_overdue_reminders(db, today=date(2020, 1, 2))
    assert count == 1
    assert reminder.status == "overdue"
