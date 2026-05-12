import pytest
from datetime import date

from app.models.hospital import HospitalEvent


class TestHospitalEventCreate:
    async def test_create_event_success(self, auth_client, test_member):
        payload = {
            "member_id": test_member.id,
            "hospital": "测试医院",
            "department": "内科",
            "admission_date": "2024-06-01",
            "discharge_date": "2024-06-10",
            "diagnosis": "肺炎",
            "doctor": "张医生",
            "key_nodes": [
                {"date": "2024-06-01", "event": "入院", "notes": "急诊入院"},
            ],
            "watch_indicators": ["systolic_bp"],
        }
        resp = await auth_client.post("/api/hospital-events", json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["hospital"] == "测试医院"
        assert data["status"] == "discharged"
        assert data["member_id"] == test_member.id

    async def test_create_active_event_no_discharge(self, auth_client, test_member):
        payload = {
            "member_id": test_member.id,
            "hospital": "测试医院",
            "admission_date": "2024-06-01",
        }
        resp = await auth_client.post("/api/hospital-events", json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "active"
        assert data["discharge_date"] is None

    async def test_create_event_forbidden_other_family(self, auth_client, db):
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
            "hospital": "测试医院",
            "admission_date": "2024-06-01",
        }
        resp = await auth_client.post("/api/hospital-events", json=payload)
        assert resp.status_code == 403

    async def test_create_event_invalid_dates(self, auth_client, test_member):
        payload = {
            "member_id": test_member.id,
            "hospital": "测试医院",
            "admission_date": "2024-06-10",
            "discharge_date": "2024-06-01",
        }
        resp = await auth_client.post("/api/hospital-events", json=payload)
        assert resp.status_code == 422


class TestHospitalEventList:
    async def test_list_events_by_member(self, auth_client, test_member, db):
        db.add(HospitalEvent(
            member_id=test_member.id,
            hospital="测试医院",
            department="内科",
            admission_date=date(2024, 6, 1),
            discharge_date=date(2024, 6, 10),
            diagnosis="肺炎",
            status="discharged",
        ))
        await db.commit()

        resp = await auth_client.get(f"/api/hospital-events?member_id={test_member.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1
        assert data[0]["hospital"] == "测试医院"

    async def test_list_events_filter_status(self, auth_client, test_member, db):
        db.add(HospitalEvent(
            member_id=test_member.id,
            hospital="医院A",
            admission_date=date(2024, 6, 1),
            status="active",
        ))
        db.add(HospitalEvent(
            member_id=test_member.id,
            hospital="医院B",
            admission_date=date(2024, 5, 1),
            discharge_date=date(2024, 5, 5),
            status="discharged",
        ))
        await db.commit()

        resp = await auth_client.get(f"/api/hospital-events?member_id={test_member.id}&status=active")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert all(e["status"] == "active" for e in data)


class TestHospitalEventUpdate:
    async def test_update_event(self, auth_client, test_member, db):
        event = HospitalEvent(
            member_id=test_member.id,
            hospital="旧医院",
            admission_date=date(2024, 6, 1),
            status="active",
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        resp = await auth_client.patch(
            f"/api/hospital-events/{event.id}",
            json={"hospital": "新医院", "discharge_date": "2024-06-15"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["hospital"] == "新医院"
        assert data["status"] == "discharged"

    async def test_update_event_not_found(self, auth_client):
        resp = await auth_client.patch(
            "/api/hospital-events/nonexistent-id",
            json={"hospital": "新医院"},
        )
        assert resp.status_code == 404

    async def test_update_event_forbidden_other_family(self, auth_client, db):
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

        event = HospitalEvent(
            member_id=other.id,
            hospital="医院",
            admission_date=date(2024, 6, 1),
            status="active",
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        resp = await auth_client.patch(
            f"/api/hospital-events/{event.id}",
            json={"hospital": "新医院"},
        )
        assert resp.status_code == 403


class TestHospitalEventDelete:
    async def test_delete_event(self, auth_client, test_member, db):
        event = HospitalEvent(
            member_id=test_member.id,
            hospital="测试医院",
            admission_date=date(2024, 6, 1),
            status="active",
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        resp = await auth_client.delete(f"/api/hospital-events/{event.id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] is True

    async def test_delete_event_not_found(self, auth_client):
        resp = await auth_client.delete("/api/hospital-events/nonexistent-id")
        assert resp.status_code == 404


class TestHospitalWatchIndicators:
    async def test_watch_indicators_empty(self, auth_client, test_member, db):
        event = HospitalEvent(
            member_id=test_member.id,
            hospital="测试医院",
            admission_date=date(2024, 6, 1),
            status="active",
            watch_indicators=["systolic_bp", "diastolic_bp"],
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        resp = await auth_client.get(f"/api/hospital-events/{event.id}/watch")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data == []

    async def test_watch_indicators_with_data(self, auth_client, test_member, db):
        from app.models.indicator import IndicatorData
        from decimal import Decimal

        event = HospitalEvent(
            member_id=test_member.id,
            hospital="测试医院",
            admission_date=date(2024, 6, 1),
            status="active",
            watch_indicators=["systolic_bp"],
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        # Add indicator records
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=Decimal("120.0"),
            unit="mmHg",
            status="normal",
            record_date=date(2024, 6, 2),
            source_hospital_id=event.id,
        ))
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=Decimal("130.0"),
            unit="mmHg",
            status="high",
            record_date=date(2024, 6, 3),
            source_hospital_id=event.id,
        ))
        await db.commit()

        resp = await auth_client.get(f"/api/hospital-events/{event.id}/watch")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["indicator_key"] == "systolic_bp"
        assert data[0]["value"] == 130.0
        assert data[0]["previous_value"] == 120.0
        assert data[0]["change"] == 10.0
        assert data[0]["status"] == "high"

    async def test_watch_indicators_forbidden(self, auth_client, db):
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

        event = HospitalEvent(
            member_id=other.id,
            hospital="测试医院",
            admission_date=date(2024, 6, 1),
            status="active",
            watch_indicators=["systolic_bp"],
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        resp = await auth_client.get(f"/api/hospital-events/{event.id}/watch")
        assert resp.status_code == 403

    async def test_watch_indicators_not_found(self, auth_client):
        resp = await auth_client.get("/api/hospital-events/nonexistent-id/watch")
        assert resp.status_code == 404


class TestHospitalCompare:
    async def test_compare_today_yesterday(self, auth_client, test_member, db):
        from app.models.indicator import IndicatorData
        from decimal import Decimal
        from datetime import timedelta

        event = HospitalEvent(
            member_id=test_member.id,
            hospital="测试医院",
            admission_date=date.today() - timedelta(days=5),
            status="active",
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        today = date.today()
        yesterday = today - timedelta(days=1)

        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="fasting_glucose",
            indicator_name="空腹血糖",
            value=Decimal("5.0"),
            unit="mmol/L",
            status="normal",
            record_date=yesterday,
            source_hospital_id=event.id,
        ))
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="fasting_glucose",
            indicator_name="空腹血糖",
            value=Decimal("6.5"),
            unit="mmol/L",
            status="high",
            record_date=today,
            source_hospital_id=event.id,
        ))
        await db.commit()

        resp = await auth_client.get(f"/api/hospital-events/{event.id}/compare")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["event_id"] == event.id
        assert data["today"] == today.isoformat()
        assert data["yesterday"] == yesterday.isoformat()
        assert data["total"] == 1
        assert data["worsened"] == 1
        assert data["stable"] == 0
        assert len(data["indicators"]) == 1
        assert data["indicators"][0]["indicator_key"] == "fasting_glucose"
        assert data["indicators"][0]["change"] == 1.5

    async def test_compare_no_data(self, auth_client, test_member, db):
        from datetime import timedelta
        event = HospitalEvent(
            member_id=test_member.id,
            hospital="测试医院",
            admission_date=date.today() - timedelta(days=5),
            status="active",
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        resp = await auth_client.get(f"/api/hospital-events/{event.id}/compare")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 0
        assert data["indicators"] == []

    async def test_compare_forbidden(self, auth_client, db):
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

        event = HospitalEvent(
            member_id=other.id,
            hospital="测试医院",
            admission_date=date(2024, 6, 1),
            status="active",
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        resp = await auth_client.get(f"/api/hospital-events/{event.id}/compare")
        assert resp.status_code == 403

    async def test_compare_not_found(self, auth_client):
        resp = await auth_client.get("/api/hospital-events/nonexistent-id/compare")
        assert resp.status_code == 404
