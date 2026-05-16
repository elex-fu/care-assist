import pytest
from datetime import date

from app.models.medication import Medication, MedicationLog


class TestMedicationCreate:
    async def test_create_medication_success(self, auth_client, test_member):
        payload = {
            "member_id": test_member.id,
            "name": "氨氯地平",
            "dosage": "5mg",
            "frequency": "每日1次",
            "time_slots": ["08:00"],
            "start_date": "2024-06-01",
            "end_date": "2024-06-30",
            "notes": "早餐后服用",
            "status": "active",
        }
        resp = await auth_client.post("/api/medications", json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "氨氯地平"
        assert data["dosage"] == "5mg"
        assert data["time_slots"] == ["08:00"]
        assert data["status"] == "active"

    async def test_create_medication_invalid_status(self, auth_client, test_member):
        payload = {
            "member_id": test_member.id,
            "name": "测试药",
            "dosage": "1片",
            "frequency": "每日1次",
            "time_slots": ["08:00"],
            "start_date": "2024-06-01",
            "status": "invalid_status",
        }
        resp = await auth_client.post("/api/medications", json=payload)
        assert resp.status_code == 422

    async def test_create_medication_forbidden_other_family(self, auth_client, db):
        from app.models.member import Member
        from app.models.family import Family
        import uuid, secrets

        other_family = Family(
            id=str(uuid.uuid4()),
            name="其他家庭",
            invite_code=secrets.token_urlsafe(8)[:6].upper(),
        )
        db.add(other_family)
        await db.flush()

        other_member = Member(
            id=str(uuid.uuid4()),
            family_id=other_family.id,
            name="其他成员",
            gender="female",
            type="adult",
            role="member",
            wx_openid=f"mock_openid_{uuid.uuid4().hex[:16]}",
        )
        db.add(other_member)
        await db.commit()

        payload = {
            "member_id": other_member.id,
            "name": "测试药",
            "dosage": "1片",
            "frequency": "每日1次",
            "time_slots": ["08:00"],
            "start_date": "2024-06-01",
        }
        resp = await auth_client.post("/api/medications", json=payload)
        assert resp.status_code == 403


class TestMedicationList:
    async def test_list_medications(self, auth_client, test_member, db):
        db.add(Medication(
            member_id=test_member.id,
            name="降压药",
            dosage="5mg",
            frequency="每日1次",
            time_slots=["08:00"],
            start_date=date(2024, 6, 1),
            status="active",
        ))
        db.add(Medication(
            member_id=test_member.id,
            name="维生素D",
            dosage="1片",
            frequency="每日1次",
            time_slots=["20:00"],
            start_date=date(2024, 6, 1),
            status="paused",
        ))
        await db.commit()

        resp = await auth_client.get(f"/api/medications?member_id={test_member.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2

    async def test_list_medications_filter_status(self, auth_client, test_member, db):
        db.add(Medication(
            member_id=test_member.id,
            name="降压药",
            dosage="5mg",
            frequency="每日1次",
            time_slots=["08:00"],
            start_date=date(2024, 6, 1),
            status="active",
        ))
        await db.commit()

        resp = await auth_client.get(f"/api/medications?member_id={test_member.id}&status=active")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["status"] == "active"


class TestMedicationDetail:
    async def test_get_medication_with_logs(self, auth_client, test_member, db):
        med = Medication(
            member_id=test_member.id,
            name="降压药",
            dosage="5mg",
            frequency="每日1次",
            time_slots=["08:00"],
            start_date=date(2024, 6, 1),
            status="active",
        )
        db.add(med)
        await db.flush()

        today = date.today()
        db.add(MedicationLog(
            medication_id=med.id,
            member_id=test_member.id,
            scheduled_date=today,
            scheduled_time="08:00",
            status="taken",
        ))
        db.add(MedicationLog(
            medication_id=med.id,
            member_id=test_member.id,
            scheduled_date=today,
            scheduled_time="20:00",
            status="pending",
        ))
        await db.commit()

        resp = await auth_client.get(f"/api/medications/{med.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["medication"]["name"] == "降压药"
        assert data["adherence_rate"] == 50.0
        assert len(data["logs"]) == 2

    async def test_get_medication_not_found(self, auth_client):
        resp = await auth_client.get("/api/medications/non-existent-id")
        assert resp.status_code == 404


class TestMedicationUpdate:
    async def test_update_medication(self, auth_client, test_member, db):
        med = Medication(
            member_id=test_member.id,
            name="降压药",
            dosage="5mg",
            frequency="每日1次",
            time_slots=["08:00"],
            start_date=date(2024, 6, 1),
            status="active",
        )
        db.add(med)
        await db.commit()

        resp = await auth_client.patch(f"/api/medications/{med.id}", json={"dosage": "10mg", "status": "paused"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["dosage"] == "10mg"
        assert data["status"] == "paused"


class TestMedicationDelete:
    async def test_delete_medication(self, auth_client, test_member, db):
        med = Medication(
            member_id=test_member.id,
            name="临时药",
            dosage="1片",
            frequency="每日1次",
            time_slots=["08:00"],
            start_date=date(2024, 6, 1),
            status="active",
        )
        db.add(med)
        await db.commit()

        resp = await auth_client.delete(f"/api/medications/{med.id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] is True


class TestMedicationTake:
    async def test_take_medication_new_log(self, auth_client, test_member, db):
        med = Medication(
            member_id=test_member.id,
            name="降压药",
            dosage="5mg",
            frequency="每日1次",
            time_slots=["08:00"],
            start_date=date(2024, 6, 1),
            status="active",
        )
        db.add(med)
        await db.commit()

        payload = {
            "scheduled_date": str(date.today()),
            "scheduled_time": "08:00",
            "notes": "饭后服用",
        }
        resp = await auth_client.post(f"/api/medications/{med.id}/take", json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "taken"
        assert data["notes"] == "饭后服用"

    async def test_take_medication_update_existing(self, auth_client, test_member, db):
        med = Medication(
            member_id=test_member.id,
            name="降压药",
            dosage="5mg",
            frequency="每日1次",
            time_slots=["08:00"],
            start_date=date(2024, 6, 1),
            status="active",
        )
        db.add(med)
        await db.flush()

        log = MedicationLog(
            medication_id=med.id,
            member_id=test_member.id,
            scheduled_date=date.today(),
            scheduled_time="08:00",
            status="pending",
        )
        db.add(log)
        await db.commit()

        payload = {
            "scheduled_date": str(date.today()),
            "scheduled_time": "08:00",
            "notes": "补打卡",
        }
        resp = await auth_client.post(f"/api/medications/{med.id}/take", json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "taken"
        assert data["notes"] == "补打卡"
