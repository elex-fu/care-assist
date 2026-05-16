"""Export endpoints integration tests."""

from datetime import date
from decimal import Decimal

from app.models.indicator import IndicatorData
from app.models.report import Report
from app.models.health_event import HealthEvent
from app.models.member import Member
from app.models.family import Family


class TestExportExcel:
    async def test_export_excel_requires_auth(self, client):
        res = await client.get("/api/export/excel?member_id=any")
        assert res.status_code == 401

    async def test_export_excel_success(self, auth_client, test_member, db):
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=Decimal("120"),
            unit="mmHg",
            status="normal",
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
        await db.commit()

        res = await auth_client.get(f"/api/export/excel?member_id={test_member.id}")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert "attachment" in res.headers["content-disposition"]
        assert "filename*=UTF-8" in res.headers["content-disposition"]

    async def test_export_excel_date_filter(self, auth_client, test_member, db):
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=Decimal("120"),
            unit="mmHg",
            status="normal",
            record_date=date(2024, 1, 10),
        ))
        await db.commit()

        res = await auth_client.get(
            f"/api/export/excel?member_id={test_member.id}&start_date=2024-01-01&end_date=2024-01-31"
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    async def test_export_excel_forbidden_other_family(self, auth_client, db):
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

        res = await auth_client.get(f"/api/export/excel?member_id={other.id}")
        assert res.status_code == 403


class TestExportPdf:
    async def test_export_pdf_requires_auth(self, client):
        res = await client.get("/api/export/pdf?member_id=any")
        assert res.status_code == 401

    async def test_export_pdf_success(self, auth_client, test_member, db):
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=Decimal("120"),
            unit="mmHg",
            status="normal",
            record_date=date(2024, 6, 15),
        ))
        await db.commit()

        res = await auth_client.get(f"/api/export/pdf?member_id={test_member.id}")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert "attachment" in res.headers["content-disposition"]
        assert "filename*=UTF-8" in res.headers["content-disposition"]

    async def test_export_pdf_forbidden_other_family(self, auth_client, db):
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

        res = await auth_client.get(f"/api/export/pdf?member_id={other.id}")
        assert res.status_code == 403
