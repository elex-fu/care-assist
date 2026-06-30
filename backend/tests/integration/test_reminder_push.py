from datetime import date
from unittest.mock import patch

import pytest

from app.core.reminder_engine import ReminderEngine
from app.models.medication import Medication, MedicationLog
from app.models.reminder import Reminder
from app.models.vaccine import VaccineRecord

SEND_PATCH = "app.services.wechat_service.WeChatService.send_subscribe_message"
MED_TMPL_PATCH = "app.services.notification_service.settings.REMINDER_MEDICATION_TEMPLATE_ID"
VAC_TMPL_PATCH = "app.services.notification_service.settings.REMINDER_VACCINE_TEMPLATE_ID"


@pytest.mark.asyncio
async def test_scan_missed_medications_sends_push(db, test_member):
    test_member.wx_openid = "openid_medication_test"
    await db.commit()

    med = Medication(
        member_id=test_member.id,
        name="测试降压药",
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

    with patch(SEND_PATCH) as mock_send, patch(MED_TMPL_PATCH, "tmpl_med"):
        mock_send.return_value = {"errcode": 0, "errmsg": "ok"}
        count = await ReminderEngine.scan_missed_medications(db, today=date(2020, 1, 2))

    assert count >= 1
    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args.kwargs
    assert call_kwargs["openid"] == "openid_medication_test"
    assert call_kwargs["template_id"] == "tmpl_med"
    assert call_kwargs["page"] == "/pkg-medication/pages/medication/medication"


@pytest.mark.asyncio
async def test_scan_overdue_vaccines_sends_push(db, test_member):
    test_member.wx_openid = "openid_vaccine_test"
    await db.commit()

    rec = VaccineRecord(
        member_id=test_member.id,
        vaccine_name="测试疫苗",
        dose=1,
        scheduled_date=date(2020, 1, 1),
        status="pending",
    )
    db.add(rec)
    await db.commit()

    with patch(SEND_PATCH) as mock_send, patch(VAC_TMPL_PATCH, "tmpl_vaccine"):
        mock_send.return_value = {"errcode": 0, "errmsg": "ok"}
        count = await ReminderEngine.scan_overdue_vaccines(db, today=date(2020, 1, 2))

    assert count == 1
    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args.kwargs
    assert call_kwargs["openid"] == "openid_vaccine_test"
    assert call_kwargs["template_id"] == "tmpl_vaccine"
    assert call_kwargs["page"] == "/pkg-child/pages/vaccine/vaccine"


@pytest.mark.asyncio
async def test_push_skipped_when_member_has_no_openid(db, test_member):
    test_member.wx_openid = None
    await db.commit()

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

    with patch(SEND_PATCH) as mock_send, patch(MED_TMPL_PATCH, "tmpl_med"):
        await ReminderEngine.scan_missed_medications(db, today=date(2020, 1, 2))

    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_push_failure_does_not_break_engine(db, test_member):
    test_member.wx_openid = "openid_push_fail"
    await db.commit()

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

    with patch(SEND_PATCH, side_effect=RuntimeError("network")) as mock_send, patch(
        MED_TMPL_PATCH, "tmpl_med"
    ):
        count = await ReminderEngine.scan_missed_medications(db, today=date(2020, 1, 2))

    assert count >= 1
    mock_send.assert_called_once()

    reminders = await db.execute(
        Reminder.__table__.select().where(Reminder.member_id == test_member.id)
    )
    assert len(reminders.scalars().all()) >= 1
