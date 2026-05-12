import pytest
from datetime import date

from app.models.vaccine import VaccineRecord


class TestVaccineRecordCreate:
    async def test_create_record_success(self, auth_client, test_member):
        payload = {
            "member_id": test_member.id,
            "vaccine_name": "乙肝疫苗",
            "dose": 1,
            "scheduled_date": "2024-06-01",
            "status": "pending",
        }
        resp = await auth_client.post("/api/vaccines", json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["vaccine_name"] == "乙肝疫苗"
        assert data["dose"] == 1
        assert data["status"] == "pending"
        assert data["member_id"] == test_member.id

    async def test_create_completed_record(self, auth_client, test_member):
        payload = {
            "member_id": test_member.id,
            "vaccine_name": "卡介苗",
            "dose": 1,
            "scheduled_date": "2024-05-01",
            "actual_date": "2024-05-01",
            "status": "completed",
            "location": "社区医院",
            "batch_no": "B123",
            "reaction": "无",
        }
        resp = await auth_client.post("/api/vaccines", json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "completed"
        assert data["actual_date"] == "2024-05-01"

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
            "vaccine_name": "乙肝疫苗",
            "dose": 1,
            "scheduled_date": "2024-06-01",
        }
        resp = await auth_client.post("/api/vaccines", json=payload)
        assert resp.status_code == 403

    async def test_create_invalid_dose(self, auth_client, test_member):
        payload = {
            "member_id": test_member.id,
            "vaccine_name": "乙肝疫苗",
            "dose": 0,
            "scheduled_date": "2024-06-01",
        }
        resp = await auth_client.post("/api/vaccines", json=payload)
        assert resp.status_code == 422


class TestVaccineRecordList:
    async def test_list_records_by_member(self, auth_client, test_member, db):
        db.add(VaccineRecord(
            member_id=test_member.id,
            vaccine_name="乙肝疫苗",
            dose=1,
            scheduled_date=date(2024, 6, 1),
            status="pending",
        ))
        await db.commit()

        resp = await auth_client.get(f"/api/vaccines?member_id={test_member.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1
        assert data[0]["vaccine_name"] == "乙肝疫苗"

    async def test_list_records_filter_status(self, auth_client, test_member, db):
        db.add(VaccineRecord(
            member_id=test_member.id,
            vaccine_name="疫苗A",
            dose=1,
            scheduled_date=date(2024, 6, 1),
            status="completed",
        ))
        db.add(VaccineRecord(
            member_id=test_member.id,
            vaccine_name="疫苗B",
            dose=1,
            scheduled_date=date(2024, 7, 1),
            status="pending",
        ))
        await db.commit()

        resp = await auth_client.get(f"/api/vaccines?member_id={test_member.id}&status=completed")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert all(r["status"] == "completed" for r in data)


class TestVaccineRecordUpdate:
    async def test_update_record(self, auth_client, test_member, db):
        record = VaccineRecord(
            member_id=test_member.id,
            vaccine_name="乙肝疫苗",
            dose=1,
            scheduled_date=date(2024, 6, 1),
            status="pending",
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        resp = await auth_client.patch(
            f"/api/vaccines/{record.id}",
            json={"status": "completed", "actual_date": "2024-06-01", "location": "社区医院"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "completed"
        assert data["location"] == "社区医院"

    async def test_update_record_not_found(self, auth_client):
        resp = await auth_client.patch(
            "/api/vaccines/nonexistent-id",
            json={"status": "completed"},
        )
        assert resp.status_code == 404

    async def test_update_record_forbidden_other_family(self, auth_client, db):
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

        record = VaccineRecord(
            member_id=other.id,
            vaccine_name="乙肝疫苗",
            dose=1,
            scheduled_date=date(2024, 6, 1),
            status="pending",
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        resp = await auth_client.patch(
            f"/api/vaccines/{record.id}",
            json={"status": "completed"},
        )
        assert resp.status_code == 403


class TestVaccineRecordDelete:
    async def test_delete_record(self, auth_client, test_member, db):
        record = VaccineRecord(
            member_id=test_member.id,
            vaccine_name="乙肝疫苗",
            dose=1,
            scheduled_date=date(2024, 6, 1),
            status="pending",
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        resp = await auth_client.delete(f"/api/vaccines/{record.id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] is True

    async def test_delete_record_not_found(self, auth_client):
        resp = await auth_client.delete("/api/vaccines/nonexistent-id")
        assert resp.status_code == 404
