from datetime import date

import pytest

from app.models.medication import Medication
from app.services.medication_log_service import MedicationLogService


@pytest.mark.asyncio
async def test_generate_for_range(db, test_member):
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

    count = await MedicationLogService.generate_for_range(
        db, test_member.id, date(2020, 1, 1), date(2020, 1, 3)
    )
    assert count == 3

    count2 = await MedicationLogService.generate_for_range(
        db, test_member.id, date(2020, 1, 1), date(2020, 1, 3)
    )
    assert count2 == 0  # idempotent


@pytest.mark.asyncio
async def test_generate_for_range_inactive_medication(db, test_member):
    med = Medication(
        member_id=test_member.id,
        name="停用药物",
        dosage="1片",
        frequency="daily",
        time_slots=["08:00"],
        start_date=date(2020, 1, 1),
        status="completed",
    )
    db.add(med)
    await db.flush()

    count = await MedicationLogService.generate_for_range(
        db, test_member.id, date(2020, 1, 1), date(2020, 1, 3)
    )
    assert count == 0
