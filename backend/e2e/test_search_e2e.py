"""E2E tests for search endpoints."""

import json

import pytest
from playwright.async_api import async_playwright

from e2e.conftest import BASE_URL


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
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="e2e/screenshots/swagger_search.png", full_page=False)

        await browser.close()


@pytest.mark.asyncio
async def test_api_search_flow_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create an indicator
    resp = await api_context.request.post(
        f"{BASE_URL}/api/indicators",
        headers=auth_headers,
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
    resp = await api_context.request.post(
        f"{BASE_URL}/api/reminders",
        headers=auth_headers,
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
    resp = await api_context.request.get(
        f"{BASE_URL}/api/search?q=收缩压",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert any(r["entity_type"] == "indicator" for r in data["data"])

    # Search reminders
    resp = await api_context.request.get(
        f"{BASE_URL}/api/search?q=体检",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert any(r["entity_type"] == "reminder" for r in data["data"])

    # Filter by entity type
    resp = await api_context.request.get(
        f"{BASE_URL}/api/search?q=收缩压&entity_types=indicator",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert all(r["entity_type"] == "indicator" for r in data["data"])

    # Search with member filter
    resp = await api_context.request.get(
        f"{BASE_URL}/api/search?q=体检&member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert all(r["member_id"] == member_id for r in data["data"])

    # No results search
    resp = await api_context.request.get(
        f"{BASE_URL}/api/search?q=xyz123不存在",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"] == []
