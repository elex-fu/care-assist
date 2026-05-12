import pytest
from datetime import date, time
from decimal import Decimal

from app.models.indicator import IndicatorData
from app.core.indicator_engine import IndicatorEngine


class TestIndicatorCreate:
    async def test_create_indicator_success(self, auth_client, test_member, db):
        payload = {
            "member_id": test_member.id,
            "indicator_key": "systolic_bp",
            "indicator_name": "收缩压",
            "value": 125.0,
            "unit": "mmHg",
            "record_date": "2024-06-15",
        }
        resp = await auth_client.post("/api/indicators", json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["indicator_key"] == "systolic_bp"
        assert data["status"] == "normal"
        assert data["member_id"] == test_member.id

    async def test_create_critical_indicator(self, auth_client, test_member, db):
        payload = {
            "member_id": test_member.id,
            "indicator_key": "systolic_bp",
            "indicator_name": "收缩压",
            "value": 200.0,
            "unit": "mmHg",
            "record_date": "2024-06-15",
        }
        resp = await auth_client.post("/api/indicators", json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "critical"

    async def test_create_indicator_forbidden_other_family(self, auth_client, db):
        # Create another family/member
        from app.models.family import Family
        from app.models.member import Member
        import uuid
        family = Family(id=str(uuid.uuid4()), name="Other", invite_code="OTHER01")
        db.add(family)
        await db.commit()
        other = Member(
            id=str(uuid.uuid4()), family_id=family.id, name="Other",
            gender="male", type="adult", role="member",
        )
        db.add(other)
        await db.commit()

        payload = {
            "member_id": other.id,
            "indicator_key": "systolic_bp",
            "indicator_name": "收缩压",
            "value": 120.0,
            "unit": "mmHg",
            "record_date": "2024-06-15",
        }
        resp = await auth_client.post("/api/indicators", json=payload)
        assert resp.status_code == 403


class TestIndicatorList:
    async def test_list_indicators_by_member(self, auth_client, test_member, db):
        # Seed data
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

        resp = await auth_client.get(f"/api/indicators?member_id={test_member.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1
        assert data[0]["indicator_key"] == "systolic_bp"

    async def test_list_indicators_filter_by_key(self, auth_client, test_member, db):
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="diastolic_bp",
            indicator_name="舒张压",
            value=Decimal("80"),
            unit="mmHg",
            status="normal",
            deviation_percent=Decimal("0.00"),
            record_date=date(2024, 6, 15),
        ))
        await db.commit()

        resp = await auth_client.get(
            f"/api/indicators?member_id={test_member.id}&indicator_key=diastolic_bp"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert all(i["indicator_key"] == "diastolic_bp" for i in data)


class TestIndicatorDelete:
    async def test_delete_indicator(self, auth_client, test_member, db):
        indicator = IndicatorData(
            member_id=test_member.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=Decimal("120"),
            unit="mmHg",
            status="normal",
            deviation_percent=Decimal("0.00"),
            record_date=date(2024, 6, 15),
        )
        db.add(indicator)
        await db.commit()
        await db.refresh(indicator)

        resp = await auth_client.delete(f"/api/indicators/{indicator.id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] is True

    async def test_delete_indicator_not_found(self, auth_client):
        resp = await auth_client.delete("/api/indicators/nonexistent-id")
        assert resp.status_code == 404


class TestIndicatorTrend:
    async def test_trend_requires_key(self, auth_client, test_member):
        resp = await auth_client.get(f"/api/indicators/trend?member_id={test_member.id}")
        assert resp.status_code == 422

    async def test_trend_returns_data(self, auth_client, test_member, db):
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=Decimal("120"),
            unit="mmHg",
            status="normal",
            deviation_percent=Decimal("0.00"),
            record_date=date(2024, 6, 10),
        ))
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=Decimal("125"),
            unit="mmHg",
            status="normal",
            deviation_percent=Decimal("0.00"),
            record_date=date(2024, 6, 15),
        ))
        await db.commit()

        resp = await auth_client.get(
            f"/api/indicators/trend?member_id={test_member.id}&indicator_key=systolic_bp"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["indicator_key"] == "systolic_bp"
        assert "trend" in data
