"""E2E tests for reports endpoints."""

import pytest
from playwright.async_api import async_playwright

from e2e.conftest import BASE_URL


@pytest.mark.asyncio
async def test_swagger_docs_show_reports():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        resp = await page.request.get(f"{BASE_URL}/openapi.json")
        assert resp.ok
        spec = await resp.json()
        paths = spec.get("paths", {})
        assert "/api/reports" in paths
        assert "post" in paths["/api/reports"]
        assert "get" in paths["/api/reports"]
        assert "/api/reports/{report_id}" in paths
        assert "delete" in paths["/api/reports/{report_id}"]
        assert "/api/reports/{report_id}/ocr" in paths
        assert "post" in paths["/api/reports/{report_id}/ocr"]

        await page.goto(f"{BASE_URL}/docs")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="e2e/screenshots/swagger_reports.png", full_page=False)

        await browser.close()


@pytest.mark.asyncio
async def test_api_report_flow_via_playwright(api_context, registered_user):
    member_id = registered_user["member_id"]
    token = registered_user["token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Create report with a fake image
    resp = await api_context.request.post(
        f"{BASE_URL}/api/reports",
        headers={"Authorization": f"Bearer {token}"},
        multipart={
            "member_id": member_id,
            "type": "lab",
            "hospital": "测试医院",
            "department": "内科",
            "report_date": "2024-06-15",
            "images": {
                "name": "bp_report.jpg",
                "mimeType": "image/jpeg",
                "buffer": b"fake image bytes for ocr",
            },
        },
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    report_id = data["data"]["id"]
    assert data["data"]["type"] == "lab"
    assert data["data"]["ocr_status"] == "pending"

    # List reports
    resp = await api_context.request.get(
        f"{BASE_URL}/api/reports?member_id={member_id}",
        headers=headers,
    )
    assert resp.ok
    data = await resp.json()
    assert len(data["data"]["reports"]) >= 1

    # Trigger OCR on a report with a mock image path
    resp = await api_context.request.post(
        f"{BASE_URL}/api/reports/{report_id}/ocr",
        headers=headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"]["ocr_status"] == "completed"
    assert len(data["data"]["extracted"]) > 0

    # Delete report
    resp = await api_context.request.delete(
        f"{BASE_URL}/api/reports/{report_id}",
        headers=headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"]["deleted"] is True
