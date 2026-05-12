import json
import pytest
import uuid
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_swagger_docs_show_search():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        resp = await page.request.get(f"{BASE_URL}/openapi.json")
        assert resp.ok
        spec = await resp.json()
        paths = spec.get("paths", {})
        assert "/api/search" in paths
        assert "get" in paths["/api/search"]

        await page.goto(f"{BASE_URL}/docs")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="e2e/screenshots/swagger_search.png", full_page=False)

        await browser.close()


@pytest.mark.asyncio
async def test_api_search_flow_via_playwright():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        code = f"mock_e2e_{uuid.uuid4().hex[:8]}"
        creator_name = "E2ESearchUser"

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

        # Create an indicator
        resp = await context.request.post(
            f"{BASE_URL}/api/indicators",
            headers=headers,
            data=json.dumps({
                "member_id": member_id,
                "indicator_key": "systolic_bp",
                "indicator_name": "收缩压",
                "value": 125.0,
                "unit": "mmHg",
                "record_date": "2024-06-15",
            }),
        )
        assert resp.ok

        # Create a reminder
        resp = await context.request.post(
            f"{BASE_URL}/api/reminders",
            headers=headers,
            data=json.dumps({
                "member_id": member_id,
                "type": "checkup",
                "title": "体检提醒",
                "scheduled_date": "2024-08-01",
                "status": "pending",
            }),
        )
        assert resp.ok

        # Search across all types
        resp = await context.request.get(
            f"{BASE_URL}/api/search?q=收缩压",
            headers=headers,
        )
        assert resp.ok
        data = await resp.json()
        assert any(r["entity_type"] == "indicator" for r in data["data"])

        # Search reminders
        resp = await context.request.get(
            f"{BASE_URL}/api/search?q=体检",
            headers=headers,
        )
        assert resp.ok
        data = await resp.json()
        assert any(r["entity_type"] == "reminder" for r in data["data"])

        # Filter by entity type
        resp = await context.request.get(
            f"{BASE_URL}/api/search?q=收缩压&entity_types=indicator",
            headers=headers,
        )
        assert resp.ok
        data = await resp.json()
        assert all(r["entity_type"] == "indicator" for r in data["data"])

        # Search with member filter
        resp = await context.request.get(
            f"{BASE_URL}/api/search?q=体检&member_id={member_id}",
            headers=headers,
        )
        assert resp.ok
        data = await resp.json()
        assert all(r["member_id"] == member_id for r in data["data"])

        # No results search
        resp = await context.request.get(
            f"{BASE_URL}/api/search?q=xyz123不存在",
            headers=headers,
        )
        assert resp.ok
        data = await resp.json()
        assert data["data"] == []

        await context.close()
        await browser.close()
