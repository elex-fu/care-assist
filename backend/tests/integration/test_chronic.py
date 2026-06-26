from datetime import date
from decimal import Decimal

from app.models.indicator import IndicatorData


class TestChronic:
    async def test_list_chronic_packages_requires_auth(self, client):
        resp = await client.get("/api/indicators/chronic")
        assert resp.status_code == 401

    async def test_list_chronic_packages(self, auth_client):
        resp = await auth_client.get("/api/indicators/chronic")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 3
        assert any(p["package"] == "hypertension" for p in data)

    async def test_get_chronic_package_requires_auth(self, client, test_member):
        resp = await client.get(f"/api/indicators/chronic/hypertension?member_id={test_member.id}")
        assert resp.status_code == 401

    async def test_get_chronic_package_hypertension(self, auth_client, test_member, db):
        db.add(
            IndicatorData(
                member_id=test_member.id,
                indicator_key="systolic_bp",
                indicator_name="收缩压",
                value=Decimal("135"),
                unit="mmHg",
                status="normal",
                record_date=date.today(),
            )
        )
        await db.commit()

        resp = await auth_client.get(
            f"/api/indicators/chronic/hypertension?member_id={test_member.id}"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["package"] == "hypertension"
        assert data["name"] == "高血压"
        assert len(data["indicators"]) == 2
        assert any(i["key"] == "systolic_bp" and i["value"] == 135.0 for i in data["indicators"])
        assert data["summary"]

    async def test_get_chronic_package_unknown(self, auth_client, test_member):
        resp = await auth_client.get(f"/api/indicators/chronic/unknown?member_id={test_member.id}")
        assert resp.status_code == 404
