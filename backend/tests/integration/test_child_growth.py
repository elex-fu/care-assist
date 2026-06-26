from datetime import date

import pytest

from app.models.growth_record import GrowthRecord


class TestChildGrowth:
    async def test_create_growth_record_requires_auth(self, client, test_member):
        resp = await client.post("/api/child/growth", json={
            "member_id": test_member.id,
            "record_type": "height",
            "value": 80,
            "unit": "cm",
            "recorded_at": "2026-06-01",
        })
        assert resp.status_code == 401

    async def test_create_growth_record(self, auth_client, test_member):
        resp = await auth_client.post("/api/child/growth", json={
            "member_id": test_member.id,
            "record_type": "height",
            "value": 80,
            "unit": "cm",
            "recorded_at": "2026-06-01",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["member_id"] == test_member.id
        assert data["record_type"] == "height"
        assert data["value"] == 80

    async def test_list_growth_records(self, auth_client, test_member, db):
        db.add(GrowthRecord(
            member_id=test_member.id,
            record_type="weight",
            value=10.5,
            unit="kg",
            recorded_at=date(2026, 6, 1),
        ))
        await db.commit()

        resp = await auth_client.get(f"/api/child/growth?member_id={test_member.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1
        assert any(r["record_type"] == "weight" for r in data)

    async def test_list_growth_records_by_type(self, auth_client, test_member, db):
        db.add(GrowthRecord(
            member_id=test_member.id,
            record_type="height",
            value=75,
            unit="cm",
            recorded_at=date(2026, 6, 1),
        ))
        await db.commit()

        resp = await auth_client.get(f"/api/child/growth?member_id={test_member.id}&record_type=height")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert all(r["record_type"] == "height" for r in data)

    async def test_delete_growth_record(self, auth_client, test_member, db):
        record = GrowthRecord(
            member_id=test_member.id,
            record_type="head_circumference",
            value=45,
            unit="cm",
            recorded_at=date(2026, 6, 1),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        resp = await auth_client.delete(f"/api/child/growth/{record.id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] is True

    async def test_list_milestones(self, auth_client, test_member):
        resp = await auth_client.get(f"/api/child/milestones?member_id={test_member.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)

    async def test_list_milestones_requires_auth(self, client, test_member):
        resp = await client.get(f"/api/child/milestones?member_id={test_member.id}")
        assert resp.status_code == 401
