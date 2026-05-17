import json
import pytest
import uuid
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_swagger_docs_show_vaccines():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        resp = await page.request.get(f"{BASE_URL}/openapi.json")
        assert resp.ok
        spec = await resp.json()
        paths = spec.get("paths", {})
        assert "/api/vaccines" in paths
        assert "post" in paths["/api/vaccines"]
        assert "get" in paths["/api/vaccines"]
        assert "/api/vaccines/{record_id}" in paths
        assert "patch" in paths["/api/vaccines/{record_id}"]
        assert "delete" in paths["/api/vaccines/{record_id}"]

        await page.goto(f"{BASE_URL}/docs")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="e2e/screenshots/swagger_vaccines.png", full_page=False)

        await browser.close()


@pytest.mark.asyncio
async def test_api_vaccine_flow_via_playwright():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        code = f"mock_e2e_{uuid.uuid4().hex[:8]}"
        creator_name = "E2EVaccineUser"

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

        # Create pending vaccine record
        resp = await context.request.post(
            f"{BASE_URL}/api/vaccines",
            headers=headers,
            data=json.dumps({
                "member_id": member_id,
                "vaccine_name": "乙肝疫苗",
                "dose": 1,
                "scheduled_date": "2024-06-01",
                "status": "pending",
            }),
        )
        assert resp.ok, await resp.text()
        data = await resp.json()
        record_id = data["data"]["id"]
        assert data["data"]["vaccine_name"] == "乙肝疫苗"
        assert data["data"]["status"] == "pending"

        # List vaccines
        resp = await context.request.get(
            f"{BASE_URL}/api/vaccines?member_id={member_id}",
            headers=headers,
        )
        assert resp.ok
        data = await resp.json()
        assert len(data["data"]) >= 1

        # Filter by pending
        resp = await context.request.get(
            f"{BASE_URL}/api/vaccines?member_id={member_id}&status=pending",
            headers=headers,
        )
        assert resp.ok
        data = await resp.json()
        assert all(r["status"] == "pending" for r in data["data"])

        # Mark as completed
        resp = await context.request.patch(
            f"{BASE_URL}/api/vaccines/{record_id}",
            headers=headers,
            data=json.dumps({
                "status": "completed",
                "actual_date": "2024-06-01",
                "location": "社区医院",
                "batch_no": "B20240601",
                "reaction": "无不良反应",
            }),
        )
        assert resp.ok, await resp.text()
        data = await resp.json()
        assert data["data"]["status"] == "completed"
        assert data["data"]["location"] == "社区医院"

        # Delete record
        resp = await context.request.delete(
            f"{BASE_URL}/api/vaccines/{record_id}",
            headers=headers,
        )
        assert resp.ok
        data = await resp.json()
        assert data["data"]["deleted"] is True

        await context.close()
        await browser.close()
