import json
import pytest
import uuid
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_swagger_docs_show_hospital_events():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        resp = await page.request.get(f"{BASE_URL}/openapi.json")
        assert resp.ok
        spec = await resp.json()
        paths = spec.get("paths", {})
        assert "/api/hospital-events" in paths
        assert "post" in paths["/api/hospital-events"]
        assert "get" in paths["/api/hospital-events"]
        assert "/api/hospital-events/{event_id}" in paths
        assert "patch" in paths["/api/hospital-events/{event_id}"]
        assert "delete" in paths["/api/hospital-events/{event_id}"]

        await page.goto(f"{BASE_URL}/docs")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="e2e/screenshots/swagger_hospitals.png", full_page=False)

        await browser.close()


@pytest.mark.asyncio
async def test_api_hospital_event_flow_via_playwright():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        code = f"mock_e2e_{uuid.uuid4().hex[:8]}"
        creator_name = "E2EHospitalUser"

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

        # Create active hospital event
        resp = await context.request.post(
            f"{BASE_URL}/api/hospital-events",
            headers=headers,
            data=json.dumps({
                "member_id": member_id,
                "hospital": "协和医院",
                "department": "心内科",
                "admission_date": "2024-06-01",
                "diagnosis": "高血压观察",
                "doctor": "李医生",
                "key_nodes": [
                    {"date": "2024-06-01", "event": "入院", "notes": "血压180/110"},
                ],
                "watch_indicators": ["systolic_bp", "diastolic_bp"],
            }),
        )
        assert resp.ok, await resp.text()
        data = await resp.json()
        event_id = data["data"]["id"]
        assert data["data"]["hospital"] == "协和医院"
        assert data["data"]["status"] == "active"

        # List events
        resp = await context.request.get(
            f"{BASE_URL}/api/hospital-events?member_id={member_id}",
            headers=headers,
        )
        assert resp.ok
        data = await resp.json()
        assert len(data["data"]) >= 1

        # Filter by active status
        resp = await context.request.get(
            f"{BASE_URL}/api/hospital-events?member_id={member_id}&status=active",
            headers=headers,
        )
        assert resp.ok
        data = await resp.json()
        assert all(e["status"] == "active" for e in data["data"])

        # Update with discharge date
        resp = await context.request.patch(
            f"{BASE_URL}/api/hospital-events/{event_id}",
            headers=headers,
            data=json.dumps({
                "discharge_date": "2024-06-10",
                "diagnosis": "高血压，已稳定",
            }),
        )
        assert resp.ok, await resp.text()
        data = await resp.json()
        assert data["data"]["status"] == "discharged"
        assert data["data"]["discharge_date"] == "2024-06-10"

        # Delete event
        resp = await context.request.delete(
            f"{BASE_URL}/api/hospital-events/{event_id}",
            headers=headers,
        )
        assert resp.ok
        data = await resp.json()
        assert data["data"]["deleted"] is True

        await context.close()
        await browser.close()
