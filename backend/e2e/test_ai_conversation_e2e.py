"""E2E tests for AI conversation endpoints."""

import json

import pytest
from playwright.async_api import async_playwright

from e2e.conftest import BASE_URL


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
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="e2e/screenshots/swagger_ai_conversations.png", full_page=False)

        await browser.close()


@pytest.mark.asyncio
async def test_api_ai_conversation_flow_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create conversation
    resp = await api_context.request.post(
        f"{BASE_URL}/api/ai-conversations",
        headers=auth_headers,
        data=json.dumps({"member_id": member_id, "page_context": "home"}),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    conv_id = data["data"]["id"]
    assert data["data"]["member_id"] == member_id
    assert data["data"]["messages"] == []

    # Send greeting message
    resp = await api_context.request.post(
        f"{BASE_URL}/api/ai-conversations/{conv_id}/messages",
        headers=auth_headers,
        data=json.dumps({"user_message": "你好"}),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert "reply" in data["data"]
    assert len(data["data"]["messages"]) == 2

    # Send indicator question (no data yet)
    resp = await api_context.request.post(
        f"{BASE_URL}/api/ai-conversations/{conv_id}/messages",
        headers=auth_headers,
        data=json.dumps({"user_message": "血压怎么样"}),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert "还没有记录" in data["data"]["reply"] or "建议定期记录" in data["data"]["reply"]

    # List conversations
    resp = await api_context.request.get(
        f"{BASE_URL}/api/ai-conversations?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert len(data["data"]) >= 1
    assert data["data"][0]["message_count"] == 4  # 2 user + 2 assistant

    # Delete conversation
    resp = await api_context.request.delete(
        f"{BASE_URL}/api/ai-conversations/{conv_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"]["deleted"] is True
