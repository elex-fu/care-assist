import json
import pytest
import uuid
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_swagger_docs_show_indicators():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        # Verify openapi.json contains indicators endpoints
        resp = await page.request.get(f"{BASE_URL}/openapi.json")
        assert resp.ok
        spec = await resp.json()
        paths = spec.get("paths", {})
        assert "/api/indicators" in paths
        assert "post" in paths["/api/indicators"]
        assert "get" in paths["/api/indicators"]
        indicator_id_path = "/api/indicators/{indicator_id}"
        assert indicator_id_path in paths
        assert "delete" in paths[indicator_id_path]

        # Open Swagger UI and screenshot
        await page.goto(f"{BASE_URL}/docs")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="e2e/screenshots/swagger_indicators.png", full_page=False)

        await browser.close()


@pytest.mark.asyncio
async def test_api_indicator_flow_via_playwright():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        code = f"mock_e2e_{uuid.uuid4().hex[:8]}"
        creator_name = "E2E测试用户"

        # Register first
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

        # Create indicator
        resp = await context.request.post(
            f"{BASE_URL}/api/indicators",
            headers=headers,
            data=json.dumps({
                "member_id": member_id,
                "indicator_key": "systolic_bp",
                "indicator_name": "收缩压",
                "value": 135.0,
                "unit": "mmHg",
                "record_date": "2024-06-15",
            }),
        )
        assert resp.ok, await resp.text()
        data = await resp.json()
        assert data["data"]["status"] == "normal"
        assert data["data"]["indicator_key"] == "systolic_bp"
        indicator_id = data["data"]["id"]

        # List indicators
        resp = await context.request.get(
            f"{BASE_URL}/api/indicators?member_id={member_id}",
            headers=headers,
        )
        assert resp.ok
        data = await resp.json()
        assert len(data["data"]) >= 1

        # Get trend
        resp = await context.request.get(
            f"{BASE_URL}/api/indicators/trend?member_id={member_id}&indicator_key=systolic_bp",
            headers=headers,
        )
        assert resp.ok
        data = await resp.json()
        assert "trend" in data["data"]

        # Delete indicator
        resp = await context.request.delete(
            f"{BASE_URL}/api/indicators/{indicator_id}",
            headers=headers,
        )
        assert resp.ok
        data = await resp.json()
        assert data["data"]["deleted"] is True

        await context.close()
        await browser.close()


@pytest.mark.asyncio
async def test_api_batch_indicator_flow_via_playwright():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        code = f"mock_e2e_{uuid.uuid4().hex[:8]}"
        creator_name = "E2EBatchUser"

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

        # Batch create indicators
        resp = await context.request.post(
            f"{BASE_URL}/api/indicators/batch",
            headers=headers,
            data=json.dumps({
                "member_id": member_id,
                "items": [
                    {
                        "indicator_key": "systolic_bp",
                        "indicator_name": "收缩压",
                        "value": 120.0,
                        "unit": "mmHg",
                        "record_date": "2024-06-15",
                    },
                    {
                        "indicator_key": "diastolic_bp",
                        "indicator_name": "舒张压",
                        "value": 80.0,
                        "unit": "mmHg",
                        "record_date": "2024-06-15",
                    },
                ],
            }),
        )
        assert resp.ok, await resp.text()
        data = await resp.json()
        assert len(data["data"]) == 2
        assert data["data"][0]["indicator_key"] == "systolic_bp"
        assert data["data"][1]["indicator_key"] == "diastolic_bp"

        await context.close()
        await browser.close()
