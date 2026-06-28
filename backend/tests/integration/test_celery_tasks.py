from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models.medication import Medication, MedicationLog
from app.models.reminder import Reminder
from app.models.vaccine import VaccineRecord
from app.tasks.cron import (
    _task_session,
    generate_medication_logs_async,
    scan_missed_medications_async,
    scan_overdue_reminders_async,
    scan_overdue_vaccines_async,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_generate_medication_logs_creates_entries(db, test_member):
    med = Medication(
        member_id=test_member.id,
        name="测试药物",
        dosage="1片",
        frequency="daily",
        time_slots=["08:00"],
        start_date=date.today(),
        status="active",
    )
    db.add(med)
    await db.commit()

    result = await generate_medication_logs_async()
    assert result["generated"] >= 1

    logs = await db.execute(
        select(MedicationLog).where(MedicationLog.medication_id == med.id)
    )
    assert len(logs.scalars().all()) >= 1


async def _verify_in_fresh_session(model_cls, obj_id, attr, expected):
    """Verify an attribute value using a fresh DB session."""
    from app.tasks.cron import _task_session

    engine, session_maker = _task_session()
    async with session_maker() as db:
        obj = await db.get(model_cls, obj_id)
        assert getattr(obj, attr) == expected
    await engine.dispose()


async def test_scan_missed_medications_creates_reminder(db, test_member):
    med = Medication(
        member_id=test_member.id,
        name="漏服药物",
        dosage="1片",
        frequency="daily",
        time_slots=["08:00"],
        start_date=date.today() - timedelta(days=5),
        status="active",
    )
    db.add(med)
    await db.commit()
    await db.refresh(med)

    log = MedicationLog(
        medication_id=med.id,
        member_id=test_member.id,
        scheduled_date=date.today() - timedelta(days=1),
        scheduled_time="08:00",
        status="pending",
    )
    db.add(log)
    await db.commit()

    result = await scan_missed_medications_async()
    assert result["missed"] >= 1

    await _verify_in_fresh_session(MedicationLog, log.id, "status", "missed")

    engine, session_maker = _task_session()
    async with session_maker() as db2:
        reminders = await db2.execute(
            select(Reminder)
            .where(Reminder.member_id == test_member.id)
            .where(Reminder.type == "medication")
        )
        assert len(reminders.scalars().all()) >= 1
    await engine.dispose()


async def test_scan_overdue_vaccines_updates_status(db, test_member):
    record = VaccineRecord(
        member_id=test_member.id,
        vaccine_name="乙肝疫苗",
        dose=1,
        scheduled_date=date.today() - timedelta(days=1),
        status="pending",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    result = await scan_overdue_vaccines_async()
    assert result["overdue"] >= 1

    await _verify_in_fresh_session(VaccineRecord, record.id, "status", "overdue")

    engine, session_maker = _task_session()
    async with session_maker() as db2:
        reminders = await db2.execute(
            select(Reminder)
            .where(Reminder.member_id == test_member.id)
            .where(Reminder.type == "vaccine")
        )
        assert len(reminders.scalars().all()) >= 1
    await engine.dispose()


async def test_scan_overdue_reminders_updates_status(db, test_member):
    reminder = Reminder(
        member_id=test_member.id,
        type="checkup",
        title="过期提醒",
        scheduled_date=date.today() - timedelta(days=1),
        status="pending",
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)

    result = await scan_overdue_reminders_async()
    assert result["updated"] >= 1

    await _verify_in_fresh_session(Reminder, reminder.id, "status", "overdue")
