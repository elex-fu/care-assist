import json
import pytest
import uuid
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_swagger_docs_show_ai_conversations():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        resp = await page.request.get(f"{BASE_URL}/openapi.json")
        assert resp.ok
        spec = await resp.json()
        paths = spec.get("paths", {})
        assert "/api/ai-conversations" in paths
        assert "post" in paths["/api/ai-conversations"]
        assert "get" in paths["/api/ai-conversations"]
        assert "/api/ai-conversations/{conversation_id}/messages" in paths
        assert "post" in paths["/api/ai-conversations/{conversation_id}/messages"]
        assert "/api/ai-conversations/{conversation_id}" in paths
        assert "delete" in paths["/api/ai-conversations/{conversation_id}"]

        await page.goto(f"{BASE_URL}/docs")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="e2e/screenshots/swagger_ai_conversations.png", full_page=False)

        await browser.close()


@pytest.mark.asyncio
async def test_api_ai_conversation_flow_via_playwright():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        code = f"mock_e2e_{uuid.uuid4().hex[:8]}"
        creator_name = "E2EAIConvUser"

        # Register
        resp = await context.request.post(
            f"{BASE_URL}/api/auth/register?creator_name={creator_name}",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"code": code}),
        )
        assert resp.ok, await resp.text()
        body = await resp.json()
        token = body["data"]["access_token"]
        member_id = body["data"]["member"]["id"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # Create conversation
        resp = await context.request.post(
            f"{BASE_URL}/api/ai-conversations",
            headers=headers,
            data=json.dumps({"member_id": member_id, "page_context": "home"}),
        )
        assert resp.ok, await resp.text()
        data = await resp.json()
        conv_id = data["data"]["id"]
        assert data["data"]["member_id"] == member_id
        assert data["data"]["messages"] == []

        # Send greeting message
        resp = await context.request.post(
            f"{BASE_URL}/api/ai-conversations/{conv_id}/messages",
            headers=headers,
            data=json.dumps({"user_message": "你好"}),
        )
        assert resp.ok, await resp.text()
        data = await resp.json()
        assert "reply" in data["data"]
        assert len(data["data"]["messages"]) == 2

        # Send indicator question (no data yet)
        resp = await context.request.post(
            f"{BASE_URL}/api/ai-conversations/{conv_id}/messages",
            headers=headers,
            data=json.dumps({"user_message": "血压怎么样"}),
        )
        assert resp.ok, await resp.text()
        data = await resp.json()
        assert "还没有记录" in data["data"]["reply"] or "建议定期记录" in data["data"]["reply"]

        # List conversations
        resp = await context.request.get(
            f"{BASE_URL}/api/ai-conversations?member_id={member_id}",
            headers=headers,
        )
        assert resp.ok
        data = await resp.json()
        assert len(data["data"]) >= 1
        assert data["data"][0]["message_count"] == 4  # 2 user + 2 assistant

        # Delete conversation
        resp = await context.request.delete(
            f"{BASE_URL}/api/ai-conversations/{conv_id}",
            headers=headers,
        )
        assert resp.ok
        data = await resp.json()
        assert data["data"]["deleted"] is True

        await context.close()
        await browser.close()
