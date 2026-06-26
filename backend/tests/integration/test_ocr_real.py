
from app.models.report import Report


class TestOCRReal:
    async def test_trigger_ocr_creates_indicators(self, auth_client, test_member, db):
        report = Report(
            member_id=test_member.id,
            type="lab",
            images=["/tmp/fake_bp_report.png"],
            ocr_status="pending",
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        resp = await auth_client.post(f"/api/reports/{report.id}/ocr")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["ocr_status"] == "completed"
        assert len(data["extracted"]) >= 1

    async def test_trigger_ocr_requires_auth(self, client, test_member, db):
        report = Report(
            member_id=test_member.id,
            type="lab",
            images=["/tmp/fake.png"],
            ocr_status="pending",
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        resp = await client.post(f"/api/reports/{report.id}/ocr")
        assert resp.status_code == 401
