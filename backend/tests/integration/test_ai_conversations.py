import pytest
from datetime import date, datetime, timezone
from decimal import Decimal

from app.models.ai_conversation import AIConversation
from app.models.indicator import IndicatorData
from app.models.report import Report


class TestAIConversationCreate:
    async def test_create_conversation_success(self, auth_client, test_member):
        payload = {
            "member_id": test_member.id,
            "page_context": "indicator_page",
        }
        resp = await auth_client.post("/api/ai-conversations", json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["member_id"] == test_member.id
        assert data["page_context"] == "indicator_page"
        assert data["messages"] == []

    async def test_create_conversation_forbidden_other_family(self, auth_client, db):
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

        payload = {"member_id": other.id}
        resp = await auth_client.post("/api/ai-conversations", json=payload)
        assert resp.status_code == 403


class TestAIConversationList:
    async def test_list_conversations_by_member(self, auth_client, test_member, db):
        conv = AIConversation(
            member_id=test_member.id,
            page_context="home",
            messages=[{"role": "user", "content": "你好", "timestamp": "2024-06-15T10:00:00"}],
        )
        db.add(conv)
        await db.commit()

        resp = await auth_client.get(f"/api/ai-conversations?member_id={test_member.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1
        assert data[0]["member_id"] == test_member.id
        assert data[0]["message_count"] == 1


class TestAIConversationSendMessage:
    async def test_send_message_greeting(self, auth_client, test_member, db):
        conv = AIConversation(
            member_id=test_member.id,
            messages=[],
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

        resp = await auth_client.post(
            f"/api/ai-conversations/{conv.id}/messages",
            json={"user_message": "你好"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "reply" in data
        assert test_member.name in data["reply"] or "您好" in data["reply"]
        assert len(data["messages"]) == 2  # user + assistant

    async def test_send_message_with_indicators(self, auth_client, test_member, db):
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
        await db.commit()

        conv = AIConversation(member_id=test_member.id, messages=[])
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

        resp = await auth_client.post(
            f"/api/ai-conversations/{conv.id}/messages",
            json={"user_message": "血压正常吗"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "120" in data["reply"] or "正常" in data["reply"]

    async def test_send_message_with_reports(self, auth_client, test_member, db):
        db.add(Report(
            member_id=test_member.id,
            type="lab",
            images=[],
            ocr_status="completed",
            extracted_indicators=[{"indicator_key": "systolic_bp", "value": 120, "status": "normal"}],
            report_date=date(2024, 6, 15),
        ))
        await db.commit()

        conv = AIConversation(member_id=test_member.id, messages=[])
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

        resp = await auth_client.post(
            f"/api/ai-conversations/{conv.id}/messages",
            json={"user_message": "报告解读"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "报告" in data["reply"]

    async def test_send_message_not_found(self, auth_client):
        resp = await auth_client.post(
            "/api/ai-conversations/nonexistent-id/messages",
            json={"user_message": "你好"},
        )
        assert resp.status_code == 404

    async def test_send_message_forbidden_other_family(self, auth_client, db):
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

        conv = AIConversation(member_id=other.id, messages=[])
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

        resp = await auth_client.post(
            f"/api/ai-conversations/{conv.id}/messages",
            json={"user_message": "你好"},
        )
        assert resp.status_code == 403


class TestAIConversationDelete:
    async def test_delete_conversation(self, auth_client, test_member, db):
        conv = AIConversation(member_id=test_member.id, messages=[])
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

        resp = await auth_client.delete(f"/api/ai-conversations/{conv.id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] is True

    async def test_delete_conversation_not_found(self, auth_client):
        resp = await auth_client.delete("/api/ai-conversations/nonexistent-id")
        assert resp.status_code == 404
