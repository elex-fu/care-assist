from unittest.mock import AsyncMock, patch

import pytest

from app.models.ai_conversation import AIConversation


@pytest.mark.asyncio
async def test_structured_chat_returns_five_layers(auth_client, test_member, db):
    """Structured chat endpoint should return 5-layer AI response."""
    conv = AIConversation(
        member_id=test_member.id,
        page_context="home",
        messages=[],
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)

    fake_structured = {
        "answer": "您好，血压偏高。",
        "data_cards": [
            {"title": "收缩压", "value": "145 mmHg", "status": "high"}
        ],
        "suggestions": ["建议低盐饮食", "每日监测血压"],
        "follow_up_questions": ["最近有头晕吗？", "是否正在服药？"],
        "disclaimer": "本建议仅供参考，请咨询医生。",
    }

    with patch(
        "app.api.ai_conversations.AIService.generate_structured_reply",
        new_callable=AsyncMock,
    ) as mock_structured:
        mock_structured.return_value = fake_structured

        resp = await auth_client.post(
            f"/api/ai-conversations/{conv.id}/structured-messages",
            json={"user_message": "帮我看血压"},
        )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["answer"] == fake_structured["answer"]
    assert len(data["data_cards"]) == 1
    assert data["data_cards"][0]["title"] == "收缩压"
    assert len(data["suggestions"]) == 2
    assert len(data["follow_up_questions"]) == 2
    assert "参考" in data["disclaimer"] or "医生" in data["disclaimer"]
