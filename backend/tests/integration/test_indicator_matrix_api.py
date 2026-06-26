import pytest
from datetime import date
from decimal import Decimal

from app.models.indicator import IndicatorData


class TestIndicatorMatrix:
    async def test_matrix_requires_auth(self, client):
        resp = await client.get("/api/indicators/matrix?member_id=123")
        assert resp.status_code == 401

    async def test_matrix_returns_dates_and_indicators(
        self, auth_client, test_member, db
    ):
        db.add(
            IndicatorData(
                member_id=test_member.id,
                indicator_key="systolic_bp",
                indicator_name="收缩压",
                value=Decimal("120"),
                unit="mmHg",
                status="normal",
                record_date=date(2026, 6, 1),
            )
        )
        await db.commit()

        resp = await auth_client.get(
            f"/api/indicators/matrix?member_id={test_member.id}"
            "&start_date=2026-06-01&end_date=2026-06-03"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "2026-06-01" in data["dates"]
        assert "systolic_bp" in data["indicator_keys"]
        cell = data["cells"]["2026-06-01"]["systolic_bp"]
        assert cell["value"] == "120.000"
        assert cell["status"] == "normal"
