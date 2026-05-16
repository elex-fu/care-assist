"""Home dashboard integration tests."""

from app.models.indicator import IndicatorData
from app.models.report import Report
from datetime import date
from decimal import Decimal


class TestHomeDashboard:
    async def test_dashboard_requires_auth(self, client):
        res = await client.get("/api/home/dashboard")
        assert res.status_code == 401

    async def test_dashboard_returns_family_and_members(self, auth_client, test_creator, test_member, db):
        # Seed some data so member cards have content
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
        await db.commit()

        res = await auth_client.get("/api/home/dashboard")
        assert res.status_code == 200
        data = res.json()["data"]
        assert "family" in data
        assert data["family"]["id"] == test_creator.family_id
        assert "members" in data
        assert len(data["members"]) >= 1
        member_ids = [m["id"] for m in data["members"]]
        assert test_creator.id in member_ids
        assert test_member.id in member_ids

    async def test_dashboard_includes_ai_summary(self, auth_client):
        res = await auth_client.get("/api/home/dashboard")
        assert res.status_code == 200
        data = res.json()["data"]
        assert "ai_summary" in data
        assert isinstance(data["ai_summary"], str)
