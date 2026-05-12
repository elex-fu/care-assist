import pytest
from datetime import date
from decimal import Decimal

from app.models.indicator import IndicatorData
from app.models.report import Report
from app.models.health_event import HealthEvent
from app.models.reminder import Reminder


class TestSearchIndicators:
    async def test_search_indicators_by_name(self, auth_client, test_member, db):
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=Decimal("120"),
            unit="mmHg",
            status="normal",
            deviation_percent=Decimal("0.00"),
            record_date=date(2024, 6, 15),
        ))
        await db.commit()

        resp = await auth_client.get("/api/search?q=收缩压")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert any(r["entity_type"] == "indicator" and "收缩压" in r["title"] for r in data)

    async def test_search_indicators_by_member_filter(self, auth_client, test_member, db):
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=Decimal("120"),
            unit="mmHg",
            status="normal",
            deviation_percent=Decimal("0.00"),
            record_date=date(2024, 6, 15),
        ))
        await db.commit()

        resp = await auth_client.get(f"/api/search?q=收缩压&member_id={test_member.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert all(r["member_id"] == test_member.id for r in data)


class TestSearchReports:
    async def test_search_reports_by_hospital(self, auth_client, test_member, db):
        db.add(Report(
            member_id=test_member.id,
            type="lab",
            images=[],
            ocr_status="completed",
            hospital="协和医院",
            report_date=date(2024, 6, 15),
        ))
        await db.commit()

        resp = await auth_client.get("/api/search?q=协和")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert any(r["entity_type"] == "report" and "协和" in (r["subtitle"] or "") for r in data)


class TestSearchHealthEvents:
    async def test_search_events_by_diagnosis(self, auth_client, test_member, db):
        db.add(HealthEvent(
            member_id=test_member.id,
            type="visit",
            event_date=date(2024, 6, 1),
            diagnosis="高血压",
            status="abnormal",
        ))
        await db.commit()

        resp = await auth_client.get("/api/search?q=高血压")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert any(r["entity_type"] == "health_event" and "高血压" in (r["subtitle"] or "") for r in data)


class TestSearchReminders:
    async def test_search_reminders_by_title(self, auth_client, test_member, db):
        db.add(Reminder(
            member_id=test_member.id,
            type="checkup",
            title="年度体检",
            scheduled_date=date(2024, 8, 1),
            status="pending",
            priority="high",
        ))
        await db.commit()

        resp = await auth_client.get("/api/search?q=体检")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert any(r["entity_type"] == "reminder" and "体检" in r["title"] for r in data)


class TestSearchEntityTypeFilter:
    async def test_search_filter_by_entity_type(self, auth_client, test_member, db):
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=Decimal("120"),
            unit="mmHg",
            status="normal",
            deviation_percent=Decimal("0.00"),
            record_date=date(2024, 6, 15),
        ))
        db.add(Reminder(
            member_id=test_member.id,
            type="checkup",
            title="体检提醒",
            scheduled_date=date(2024, 8, 1),
            status="pending",
            priority="normal",
        ))
        await db.commit()

        resp = await auth_client.get("/api/search?q=收缩压&entity_types=indicator")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert all(r["entity_type"] == "indicator" for r in data)

    async def test_search_no_results(self, auth_client):
        resp = await auth_client.get("/api/search?q=不存在的词xyz123")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data == []


class TestSearchForbidden:
    async def test_search_forbidden_other_family(self, auth_client, db):
        from app.models.family import Family
        from app.models.member import Member
        import uuid, secrets
        family = Family(
            id=str(uuid.uuid4()), name="Other",
            invite_code=secrets.token_urlsafe(8)[:6].upper(),
        )
        db.add(family)
        await db.commit()
        other = Member(
            id=str(uuid.uuid4()), family_id=family.id, name="Other",
            gender="male", type="adult", role="member",
        )
        db.add(other)
        await db.commit()

        resp = await auth_client.get(f"/api/search?q=测试&member_id={other.id}")
        assert resp.status_code == 403
