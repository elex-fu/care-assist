import pytest
from datetime import date, time

from app.models.health_event import HealthEvent


class TestHealthEventCreate:
    async def test_create_event_success(self, auth_client, test_member):
        payload = {
            "member_id": test_member.id,
            "type": "visit",
            "event_date": "2024-06-01",
            "event_time": "10:00",
            "hospital": "测试医院",
            "department": "内科",
            "doctor": "张医生",
            "diagnosis": "感冒",
            "notes": "多喝水",
            "status": "normal",
        }
        resp = await auth_client.post("/api/health-events", json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["type"] == "visit"
        assert data["hospital"] == "测试医院"
        assert data["member_id"] == test_member.id

    async def test_create_milestone_event(self, auth_client, test_member):
        payload = {
            "member_id": test_member.id,
            "type": "milestone",
            "event_date": "2024-06-01",
            "notes": "第一次翻身",
            "status": "normal",
        }
        resp = await auth_client.post("/api/health-events", json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["type"] == "milestone"
        assert data["notes"] == "第一次翻身"

    async def test_create_forbidden_other_family(self, auth_client, db):
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

        payload = {
            "member_id": other.id,
            "type": "visit",
            "event_date": "2024-06-01",
        }
        resp = await auth_client.post("/api/health-events", json=payload)
        assert resp.status_code == 403

    async def test_create_invalid_type(self, auth_client, test_member):
        payload = {
            "member_id": test_member.id,
            "type": "invalid",
            "event_date": "2024-06-01",
        }
        resp = await auth_client.post("/api/health-events", json=payload)
        assert resp.status_code == 422


class TestHealthEventList:
    async def test_list_events_by_member(self, auth_client, test_member, db):
        db.add(HealthEvent(
            member_id=test_member.id,
            type="visit",
            event_date=date(2024, 6, 1),
            status="normal",
        ))
        await db.commit()

        resp = await auth_client.get(f"/api/health-events?member_id={test_member.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1
        assert data[0]["type"] == "visit"

    async def test_list_events_filter_type(self, auth_client, test_member, db):
        db.add(HealthEvent(
            member_id=test_member.id,
            type="lab",
            event_date=date(2024, 6, 1),
            status="normal",
        ))
        db.add(HealthEvent(
            member_id=test_member.id,
            type="visit",
            event_date=date(2024, 5, 1),
            status="normal",
        ))
        await db.commit()

        resp = await auth_client.get(f"/api/health-events?member_id={test_member.id}&type=lab")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert all(e["type"] == "lab" for e in data)


class TestHealthEventUpdate:
    async def test_update_event(self, auth_client, test_member, db):
        event = HealthEvent(
            member_id=test_member.id,
            type="visit",
            event_date=date(2024, 6, 1),
            diagnosis="感冒",
            status="normal",
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        resp = await auth_client.patch(
            f"/api/health-events/{event.id}",
            json={"diagnosis": "流感", "notes": "休息一周"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["diagnosis"] == "流感"
        assert data["notes"] == "休息一周"

    async def test_update_event_not_found(self, auth_client):
        resp = await auth_client.patch(
            "/api/health-events/nonexistent-id",
            json={"diagnosis": "流感"},
        )
        assert resp.status_code == 404


class TestHealthEventDelete:
    async def test_delete_event(self, auth_client, test_member, db):
        event = HealthEvent(
            member_id=test_member.id,
            type="visit",
            event_date=date(2024, 6, 1),
            status="normal",
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        resp = await auth_client.delete(f"/api/health-events/{event.id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] is True

    async def test_delete_event_not_found(self, auth_client):
        resp = await auth_client.delete("/api/health-events/nonexistent-id")
        assert resp.status_code == 404
