import io
from datetime import date

from app.models.report import Report


class TestReportUpload:
    async def test_upload_report_without_images(self, auth_client, test_member):
        payload = {
            "member_id": test_member.id,
            "type": "lab",
            "hospital": "测试医院",
            "department": "内科",
            "report_date": "2024-06-15",
        }
        resp = await auth_client.post("/api/reports", data=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["type"] == "lab"
        assert data["hospital"] == "测试医院"
        assert data["ocr_status"] == "pending"

    async def test_upload_report_with_images(self, auth_client, test_member):
        files = {
            "images": ("bp_report.jpg", io.BytesIO(b"fake image bytes"), "image/jpeg"),
        }
        data = {
            "member_id": test_member.id,
            "type": "lab",
            "report_date": "2024-06-15",
        }
        resp = await auth_client.post("/api/reports", data=data, files=files)
        assert resp.status_code == 200
        result = resp.json()["data"]
        assert result["type"] == "lab"
        assert len(result["images"]) == 1

    async def test_upload_forbidden_other_family(self, auth_client, db):
        import secrets
        import uuid

        from app.models.family import Family
        from app.models.member import Member
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
            "type": "lab",
            "report_date": "2024-06-15",
        }
        resp = await auth_client.post("/api/reports", data=payload)
        assert resp.status_code == 403


class TestReportList:
    async def test_list_reports_by_member(self, auth_client, test_member, db):
        db.add(Report(
            member_id=test_member.id,
            type="lab",
            images=["http://test/image1.jpg"],
            ocr_status="completed",
            report_date=date(2024, 6, 15),
        ))
        await db.commit()

        resp = await auth_client.get(f"/api/reports?member_id={test_member.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["reports"]) >= 1
        assert data["reports"][0]["type"] == "lab"


class TestReportGet:
    async def test_get_report(self, auth_client, test_member, db):
        report = Report(
            member_id=test_member.id,
            type="lab",
            images=["http://test/image1.jpg"],
            ocr_status="pending",
            report_date=date(2024, 6, 15),
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        resp = await auth_client.get(f"/api/reports/{report.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == report.id
        assert data["member_id"] == test_member.id
        assert data["type"] == "lab"
        assert data["ocr_status"] == "pending"

    async def test_get_report_not_found(self, auth_client):
        resp = await auth_client.get("/api/reports/nonexistent-id")
        assert resp.status_code == 404

    async def test_get_report_other_family(self, auth_client, db):
        import secrets
        import uuid

        from app.models.family import Family
        from app.models.member import Member
        other_family = Family(
            id=str(uuid.uuid4()), name="Other",
            invite_code=secrets.token_urlsafe(8)[:6].upper(),
        )
        db.add(other_family)
        await db.commit()
        other_member = Member(
            id=str(uuid.uuid4()), family_id=other_family.id, name="Other",
            gender="male", type="adult", role="member",
        )
        db.add(other_member)
        await db.commit()

        report = Report(
            member_id=other_member.id,
            type="lab",
            images=[],
            ocr_status="pending",
            report_date=date(2024, 6, 15),
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        resp = await auth_client.get(f"/api/reports/{report.id}")
        assert resp.status_code == 403


class TestReportDelete:
    async def test_delete_report(self, auth_client, test_member, db):
        report = Report(
            member_id=test_member.id,
            type="lab",
            images=[],
            ocr_status="pending",
            report_date=date(2024, 6, 15),
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        resp = await auth_client.delete(f"/api/reports/{report.id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] is True

    async def test_delete_report_not_found(self, auth_client):
        resp = await auth_client.delete("/api/reports/nonexistent-id")
        assert resp.status_code == 404


class TestReportOCR:
    async def test_trigger_ocr(self, auth_client, test_member, db):
        report = Report(
            member_id=test_member.id,
            type="lab",
            images=["uploads/reports/bp_report.jpg"],
            ocr_status="pending",
            report_date=date(2024, 6, 15),
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        resp = await auth_client.post(f"/api/reports/{report.id}/ocr")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["ocr_status"] == "completed"
        assert len(data["extracted"]) > 0
        assert data["extracted"][0]["indicator_key"]


class TestReportAISummary:
    async def test_generate_ai_summary_success(self, auth_client, test_member, db):
        report = Report(
            member_id=test_member.id,
            type="lab",
            images=[],
            ocr_status="completed",
            report_date=date(2024, 6, 15),
            extracted_indicators=[
                {
                    "indicator_key": "systolic_bp",
                    "indicator_name": "收缩压",
                    "value": 145,
                    "unit": "mmHg",
                    "status": "high",
                }
            ],
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        resp = await auth_client.post(f"/api/reports/{report.id}/ai-summary")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == report.id
        assert test_member.name in data["ai_summary"]
        assert "异常" in data["ai_summary"]

    async def test_generate_ai_summary_no_indicators(self, auth_client, test_member, db):
        report = Report(
            member_id=test_member.id,
            type="lab",
            images=[],
            ocr_status="completed",
            report_date=date(2024, 6, 15),
            extracted_indicators=[],
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        resp = await auth_client.post(f"/api/reports/{report.id}/ai-summary")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == report.id
        assert "暂未识别到指标" in data["ai_summary"]

    async def test_generate_ai_summary_not_found(self, auth_client):
        resp = await auth_client.post("/api/reports/nonexistent-id/ai-summary")
        assert resp.status_code == 404

    async def test_generate_ai_summary_other_family(self, auth_client, db):
        import secrets
        import uuid

        from app.models.family import Family
        from app.models.member import Member

        other_family = Family(
            id=str(uuid.uuid4()),
            name="Other",
            invite_code=secrets.token_urlsafe(8)[:6].upper(),
        )
        db.add(other_family)
        await db.commit()
        other_member = Member(
            id=str(uuid.uuid4()),
            family_id=other_family.id,
            name="Other",
            gender="male",
            type="adult",
            role="member",
        )
        db.add(other_member)
        await db.commit()

        report = Report(
            member_id=other_member.id,
            type="lab",
            images=[],
            ocr_status="completed",
            report_date=date(2024, 6, 15),
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        resp = await auth_client.post(f"/api/reports/{report.id}/ai-summary")
        assert resp.status_code == 403
