from datetime import date
from decimal import Decimal

from app.models.indicator import IndicatorData
from app.models.report import Report
from app.models.health_event import HealthEvent


class TestAnnualSummary:
    async def test_annual_summary_returns_data(self, auth_client, test_member, db):
        # Seed data
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=Decimal("120"),
            unit="mmHg",
            status="normal",
            record_date=date.today(),
        ))
        db.add(Report(
            member_id=test_member.id,
            type="lab",
            hospital="测试医院",
            report_date=date.today(),
            ocr_status="completed",
        ))
        db.add(HealthEvent(
            member_id=test_member.id,
            type="lab",
            event_date=date.today(),
            diagnosis="常规检查",
            status="normal",
        ))
        await db.commit()

        res = await auth_client.get("/api/summary/annual")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["indicator_count"] == 1
        assert data["report_count"] == 1
        assert data["event_count"] == 1
        assert data["abnormal_count"] == 0
        assert len(data["members"]) >= 1
        assert len(data["achievements"]) >= 1

    async def test_annual_summary_with_year_param(self, auth_client):
        res = await auth_client.get("/api/summary/annual?year=2023")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["year"] == 2023
