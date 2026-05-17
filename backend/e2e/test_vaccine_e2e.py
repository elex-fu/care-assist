"""E2E tests for vaccine endpoints."""

import json

import pytest
from playwright.async_api import async_playwright

from e2e.conftest import BASE_URL


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
async def test_api_vaccine_flow_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create pending vaccine record
    resp = await api_context.request.post(
        f"{BASE_URL}/api/vaccines",
        headers=auth_headers,
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
    resp = await api_context.request.get(
        f"{BASE_URL}/api/vaccines?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert len(data["data"]) >= 1

    # Filter by pending
    resp = await api_context.request.get(
        f"{BASE_URL}/api/vaccines?member_id={member_id}&status=pending",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert all(r["status"] == "pending" for r in data["data"])

    # Mark as completed
    resp = await api_context.request.patch(
        f"{BASE_URL}/api/vaccines/{record_id}",
        headers=auth_headers,
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
    resp = await api_context.request.delete(
        f"{BASE_URL}/api/vaccines/{record_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"]["deleted"] is True