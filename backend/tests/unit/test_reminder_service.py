from datetime import date, timedelta

import pytest

from app.models.reminder import Reminder
from app.services.reminder_service import find_duplicate_reminder


class TestFindDuplicateReminder:
    async def test_find_duplicate_within_one_day(self, db, test_member):
        existing = Reminder(
            member_id=test_member.id,
            type="checkup",
            title="年度体检",
            scheduled_date=date(2024, 6, 1),
            status="pending",
            related_report_id="report-1",
            related_indicator="indicator-1",
        )
        db.add(existing)
        await db.commit()

        duplicate = await find_duplicate_reminder(
            db,
            member_id=test_member.id,
            type="checkup",
            scheduled_date=date(2024, 6, 2),
            related_report_id="report-1",
            related_indicator="indicator-1",
        )
        assert duplicate is not None
        assert duplicate.id == existing.id

    async def test_no_duplicate_outside_one_day(self, db, test_member):
        existing = Reminder(
            member_id=test_member.id,
            type="checkup",
            title="年度体检",
            scheduled_date=date(2024, 6, 1),
            status="pending",
        )
        db.add(existing)
        await db.commit()

        duplicate = await find_duplicate_reminder(
            db,
            member_id=test_member.id,
            type="checkup",
            scheduled_date=date(2024, 6, 3),
            related_report_id=None,
            related_indicator=None,
        )
        assert duplicate is None

    async def test_no_duplicate_different_type(self, db, test_member):
        existing = Reminder(
            member_id=test_member.id,
            type="checkup",
            title="年度体检",
            scheduled_date=date(2024, 6, 1),
            status="pending",
        )
        db.add(existing)
        await db.commit()

        duplicate = await find_duplicate_reminder(
            db,
            member_id=test_member.id,
            type="vaccine",
            scheduled_date=date(2024, 6, 1),
            related_report_id=None,
            related_indicator=None,
        )
        assert duplicate is None

    async def test_no_duplicate_completed_status(self, db, test_member):
        existing = Reminder(
            member_id=test_member.id,
            type="checkup",
            title="年度体检",
            scheduled_date=date(2024, 6, 1),
            status="completed",
        )
        db.add(existing)
        await db.commit()

        duplicate = await find_duplicate_reminder(
            db,
            member_id=test_member.id,
            type="checkup",
            scheduled_date=date(2024, 6, 1),
            related_report_id=None,
            related_indicator=None,
        )
        assert duplicate is None

    async def test_no_duplicate_different_member(self, db, test_creator):
        existing = Reminder(
            member_id=test_creator.id,
            type="checkup",
            title="年度体检",
            scheduled_date=date(2024, 6, 1),
            status="pending",
        )
        db.add(existing)
        await db.commit()

        duplicate = await find_duplicate_reminder(
            db,
            member_id="some-other-member",
            type="checkup",
            scheduled_date=date(2024, 6, 1),
            related_report_id=None,
            related_indicator=None,
        )
        assert duplicate is None

    async def test_no_duplicate_different_report(self, db, test_member):
        existing = Reminder(
            member_id=test_member.id,
            type="review",
            title="复查A",
            scheduled_date=date(2024, 6, 1),
            status="pending",
            related_report_id="report-1",
        )
        db.add(existing)
        await db.commit()

        duplicate = await find_duplicate_reminder(
            db,
            member_id=test_member.id,
            type="review",
            scheduled_date=date(2024, 6, 1),
            related_report_id="report-2",
            related_indicator=None,
        )
        assert duplicate is None
