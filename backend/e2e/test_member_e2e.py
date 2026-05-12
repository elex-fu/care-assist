import json
import pytest
import uuid
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_swagger_docs_show_members():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        resp = await page.request.get(f"{BASE_URL}/openapi.json")
        assert resp.ok
        spec = await resp.json()
        paths = spec.get("paths", {})
        assert "/api/members/me" in paths
        assert "/api/members/{member_id}/export" in paths

        await page.goto(f"{BASE_URL}/docs")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="e2e/screenshots/swagger_members.png", full_page=False)

        await browser.close()


@pytest.mark.asyncio
async def test_api_member_export_flow_via_playwright():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        code = f"mock_e2e_{uuid.uuid4().hex[:8]}"
        creator_name = "E2EExportUser"

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
                "value": 120.0,
                "unit": "mmHg",
                "record_date": "2024-06-15",
            }),
        )
        assert resp.ok

        # Export member health data
        resp = await context.request.get(
            f"{BASE_URL}/api/members/{member_id}/export",
            headers=headers,
        )
        assert resp.ok, await resp.text()
        data = await resp.json()
        assert "member" in data["data"]
        assert len(data["data"]["indicators"]) >= 1
        assert data["data"]["member"]["name"] == creator_name

        await context.close()
        await browser.close()
