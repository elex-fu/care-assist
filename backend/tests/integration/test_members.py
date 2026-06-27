from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.models.family import Family
from app.models.health_event import HealthEvent
from app.models.hospital import HospitalEvent
from app.models.indicator import IndicatorData
from app.models.member import Member
from app.models.reminder import Reminder
from app.models.report import Report
from app.models.vaccine import VaccineRecord
from app.models.vaccine_library import VaccineLibrary


class TestMemberExport:
    async def test_export_member_health(self, auth_client, test_member, db):
        # Seed various data types
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
        db.add(Report(
            member_id=test_member.id,
            type="lab",
            hospital="测试医院",
            report_date=date(2024, 6, 15),
            ocr_status="completed",
        ))
        db.add(HealthEvent(
            member_id=test_member.id,
            type="lab",
            event_date=date(2024, 6, 15),
            diagnosis="常规检查",
            status="normal",
        ))
        db.add(HospitalEvent(
            member_id=test_member.id,
            hospital="测试医院",
            admission_date=date(2024, 6, 1),
            discharge_date=date(2024, 6, 10),
            diagnosis="肺炎",
            status="discharged",
        ))
        db.add(VaccineRecord(
            member_id=test_member.id,
            vaccine_name="乙肝疫苗",
            dose=1,
            scheduled_date=date(2024, 6, 1),
            status="completed",
        ))
        db.add(Reminder(
            member_id=test_member.id,
            title="复查提醒",
            type="review",
            scheduled_date=date(2024, 6, 20),
            status="pending",
        ))
        await db.commit()

        resp = await auth_client.get(f"/api/members/{test_member.id}/export")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "member" in data
        assert len(data["indicators"]) >= 1
        assert len(data["reports"]) >= 1
        assert len(data["health_events"]) >= 1
        assert len(data["hospital_events"]) >= 1
        assert len(data["vaccines"]) >= 1
        assert len(data["reminders"]) >= 1

    async def test_export_forbidden_other_family(self, auth_client, db):
        import secrets
        import uuid
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

        resp = await auth_client.get(f"/api/members/{other.id}/export")
        assert resp.status_code == 403

    async def test_export_member_not_found(self, auth_client):
        resp = await auth_client.get("/api/members/nonexistent-id/export")
        assert resp.status_code == 404


class TestMemberCreateVaccineSchedule:
    async def test_create_child_member_generates_vaccine_records(self, auth_client, db):
        birth_date = date(2023, 5, 10)
        resp = await auth_client.post(
            "/api/members",
            params={
                "name": "Child Member",
                "gender": "male",
                "type": "child",
                "birth_date": birth_date.isoformat(),
            },
        )
        assert resp.status_code == 200
        member_id = resp.json()["data"]["id"]

        # End the test transaction so the next query sees committed API-side data.
        await db.rollback()

        lib_count = len((await db.execute(select(VaccineLibrary.id))).scalars().all())
        assert lib_count > 0
        records = (
            await db.execute(select(VaccineRecord).where(VaccineRecord.member_id == member_id))
        ).scalars().all()
        assert len(records) == lib_count
        for record in records:
            assert record.status == "pending"
            assert record.dose >= 1
            assert record.vaccine_name
            assert record.scheduled_date >= birth_date
        # Verify at least one birth-dose record is scheduled on the birth date
        birth_dose = next((r for r in records if r.scheduled_date == birth_date), None)
        assert birth_dose is not None

    async def test_create_adult_member_does_not_generate_vaccine_records(self, auth_client, db):
        resp = await auth_client.post(
            "/api/members",
            params={
                "name": "Adult Member",
                "gender": "male",
                "type": "adult",
                "birth_date": "1990-01-01",
            },
        )
        assert resp.status_code == 200
        member_id = resp.json()["data"]["id"]

        await db.rollback()

        records = (
            await db.execute(select(VaccineRecord).where(VaccineRecord.member_id == member_id))
        ).scalars().all()
        assert len(records) == 0


class TestJoinFamilyVaccineSchedule:
    async def test_join_family_as_child_generates_vaccine_records(self, auth_client, db):
        resp = await auth_client.post("/api/members/invite")
        assert resp.status_code == 200
        token = resp.json()["data"]["invite_link"].split("token=")[1]

        birth_date = date(2022, 3, 15)
        resp = await auth_client.post(
            "/api/members/join",
            params={
                "token": token,
                "name": "Joined Child",
                "type": "child",
                "birth_date": birth_date.isoformat(),
            },
        )
        assert resp.status_code == 200
        member_id = resp.json()["data"]["id"]

        await db.rollback()

        lib_count = len((await db.execute(select(VaccineLibrary.id))).scalars().all())
        assert lib_count > 0
        records = (
            await db.execute(select(VaccineRecord).where(VaccineRecord.member_id == member_id))
        ).scalars().all()
        assert len(records) == lib_count
        for record in records:
            assert record.status == "pending"
            assert record.dose >= 1
            assert record.vaccine_name
            assert record.scheduled_date >= birth_date
        birth_dose = next((r for r in records if r.scheduled_date == birth_date), None)
        assert birth_dose is not None
