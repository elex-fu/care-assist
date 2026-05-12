import pytest
from datetime import date

from app.models.reminder import Reminder


class TestReminderCreate:
    async def test_create_reminder_success(self, auth_client, test_member):
        payload = {
            "member_id": test_member.id,
            "type": "checkup",
            "title": "年度体检",
            "description": "记得空腹",
            "scheduled_date": "2024-06-01",
            "status": "pending",
            "priority": "high",
        }
        resp = await auth_client.post("/api/reminders", json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["type"] == "checkup"
        assert data["title"] == "年度体检"
        assert data["priority"] == "high"
        assert data["member_id"] == test_member.id

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
            "type": "checkup",
            "title": "体检",
            "scheduled_date": "2024-06-01",
        }
        resp = await auth_client.post("/api/reminders", json=payload)
        assert resp.status_code == 403

    async def test_create_invalid_type(self, auth_client, test_member):
        payload = {
            "member_id": test_member.id,
            "type": "invalid",
            "title": "体检",
            "scheduled_date": "2024-06-01",
        }
        resp = await auth_client.post("/api/reminders", json=payload)
        assert resp.status_code == 422


class TestReminderList:
    async def test_list_reminders_by_member(self, auth_client, test_member, db):
        db.add(Reminder(
            member_id=test_member.id,
            type="checkup",
            title="年度体检",
            scheduled_date=date(2024, 6, 1),
            status="pending",
            priority="normal",
        ))
        await db.commit()

        resp = await auth_client.get(f"/api/reminders?member_id={test_member.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1
        assert data[0]["title"] == "年度体检"

    async def test_list_reminders_filter_status(self, auth_client, test_member, db):
        db.add(Reminder(
            member_id=test_member.id,
            type="vaccine",
            title="疫苗A",
            scheduled_date=date(2024, 6, 1),
            status="completed",
            priority="normal",
        ))
        db.add(Reminder(
            member_id=test_member.id,
            type="vaccine",
            title="疫苗B",
            scheduled_date=date(2024, 7, 1),
            status="pending",
            priority="normal",
        ))
        await db.commit()

        resp = await auth_client.get(f"/api/reminders?member_id={test_member.id}&status=completed")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert all(r["status"] == "completed" for r in data)


class TestReminderUpdate:
    async def test_update_reminder(self, auth_client, test_member, db):
        reminder = Reminder(
            member_id=test_member.id,
            type="checkup",
            title="旧标题",
            scheduled_date=date(2024, 6, 1),
            status="pending",
            priority="normal",
        )
        db.add(reminder)
        await db.commit()
        await db.refresh(reminder)

        resp = await auth_client.patch(
            f"/api/reminders/{reminder.id}",
            json={"status": "completed", "completed_date": "2024-06-01"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "completed"
        assert data["completed_date"] == "2024-06-01"

    async def test_update_reminder_not_found(self, auth_client):
        resp = await auth_client.patch(
            "/api/reminders/nonexistent-id",
            json={"status": "completed"},
        )
        assert resp.status_code == 404


class TestReminderDelete:
    async def test_delete_reminder(self, auth_client, test_member, db):
        reminder = Reminder(
            member_id=test_member.id,
            type="checkup",
            title="体检",
            scheduled_date=date(2024, 6, 1),
            status="pending",
            priority="normal",
        )
        db.add(reminder)
        await db.commit()
        await db.refresh(reminder)

        resp = await auth_client.delete(f"/api/reminders/{reminder.id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] is True

    async def test_delete_reminder_not_found(self, auth_client):
        resp = await auth_client.delete("/api/reminders/nonexistent-id")
        assert resp.status_code == 404
