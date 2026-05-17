"""E2E tests for hospital events endpoints."""

import json
from datetime import datetime, timedelta

import pytest
from playwright.async_api import async_playwright

from e2e.conftest import BASE_URL


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
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="e2e/screenshots/swagger_hospitals.png", full_page=False)

        await browser.close()


@pytest.mark.asyncio
async def test_api_hospital_event_flow_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create active hospital event
    resp = await api_context.request.post(
        f"{BASE_URL}/api/hospital-events",
        headers=auth_headers,
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
    resp = await api_context.request.get(
        f"{BASE_URL}/api/hospital-events?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert len(data["data"]) >= 1

    # Filter by active status
    resp = await api_context.request.get(
        f"{BASE_URL}/api/hospital-events?member_id={member_id}&status=active",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert all(e["status"] == "active" for e in data["data"])

    # Update with discharge date
    resp = await api_context.request.patch(
        f"{BASE_URL}/api/hospital-events/{event_id}",
        headers=auth_headers,
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
    resp = await api_context.request.delete(
        f"{BASE_URL}/api/hospital-events/{event_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"]["deleted"] is True


@pytest.mark.asyncio
async def test_api_hospital_watch_and_compare_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create hospital event with watch indicators
    resp = await api_context.request.post(
        f"{BASE_URL}/api/hospital-events",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "hospital": "同仁医院",
            "department": "心内科",
            "admission_date": "2024-06-01",
            "diagnosis": "高血压观察",
            "watch_indicators": ["systolic_bp", "diastolic_bp"],
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    event_id = data["data"]["id"]

    # Create indicators for yesterday and today
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    # Yesterday indicator
    resp = await api_context.request.post(
        f"{BASE_URL}/api/indicators",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "indicator_key": "systolic_bp",
            "indicator_name": "收缩压",
            "value": 120.0,
            "unit": "mmHg",
            "record_date": yesterday.isoformat(),
            "source_hospital_id": event_id,
        }),
    )
    assert resp.ok

    # Today indicator
    resp = await api_context.request.post(
        f"{BASE_URL}/api/indicators",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "indicator_key": "systolic_bp",
            "indicator_name": "收缩压",
            "value": 130.0,
            "unit": "mmHg",
            "record_date": today.isoformat(),
            "source_hospital_id": event_id,
        }),
    )
    assert resp.ok

    # Get watch indicators
    resp = await api_context.request.get(
        f"{BASE_URL}/api/hospital-events/{event_id}/watch",
        headers=auth_headers,
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert len(data["data"]) >= 1
    watch_item = data["data"][0]
    assert watch_item["indicator_key"] == "systolic_bp"
    assert watch_item["value"] == 130.0
    assert watch_item["previous_value"] == 120.0

    # Get comparison
    resp = await api_context.request.get(
        f"{BASE_URL}/api/hospital-events/{event_id}/compare",
        headers=auth_headers,
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert data["data"]["event_id"] == event_id
    assert data["data"]["total"] >= 1
