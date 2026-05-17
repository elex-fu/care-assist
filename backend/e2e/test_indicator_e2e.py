"""E2E tests for indicators endpoints."""

import json

import pytest
from playwright.async_api import async_playwright

from e2e.conftest import BASE_URL


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
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="e2e/screenshots/swagger_indicators.png", full_page=False)

        await browser.close()


@pytest.mark.asyncio
async def test_api_indicator_flow_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create indicator
    resp = await api_context.request.post(
        f"{BASE_URL}/api/indicators",
        headers=auth_headers,
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
    resp = await api_context.request.get(
        f"{BASE_URL}/api/indicators?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert len(data["data"]) >= 1

    # Get trend
    resp = await api_context.request.get(
        f"{BASE_URL}/api/indicators/trend?member_id={member_id}&indicator_key=systolic_bp",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert "trend" in data["data"]

    # Delete indicator
    resp = await api_context.request.delete(
        f"{BASE_URL}/api/indicators/{indicator_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"]["deleted"] is True


@pytest.mark.asyncio
async def test_api_batch_indicator_flow_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Batch create indicators
    resp = await api_context.request.post(
        f"{BASE_URL}/api/indicators/batch",
        headers=auth_headers,
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
