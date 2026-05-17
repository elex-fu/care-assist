"""E2E tests for timeline and reminder endpoints."""

import json

import pytest
from playwright.async_api import async_playwright

from e2e.conftest import BASE_URL


@pytest.mark.asyncio
async def test_swagger_docs_show_timeline_and_reminders():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        resp = await page.request.get(f"{BASE_URL}/openapi.json")
        assert resp.ok
        spec = await resp.json()
        paths = spec.get("paths", {})
        assert "/api/health-events" in paths
        assert "/api/reminders" in paths

        await page.goto(f"{BASE_URL}/docs")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="e2e/screenshots/swagger_timeline_reminders.png", full_page=False)

        await browser.close()


@pytest.mark.asyncio
async def test_api_reminder_flow_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create reminder
    resp = await api_context.request.post(
        f"{BASE_URL}/api/reminders",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "type": "checkup",
            "title": "年度体检",
            "description": "记得空腹，带身份证",
            "scheduled_date": "2024-08-01",
            "status": "pending",
            "priority": "high",
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    reminder_id = data["data"]["id"]
    assert data["data"]["type"] == "checkup"
    assert data["data"]["priority"] == "high"

    # List reminders
    resp = await api_context.request.get(
        f"{BASE_URL}/api/reminders?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert len(data["data"]) >= 1

    # Filter pending
    resp = await api_context.request.get(
        f"{BASE_URL}/api/reminders?member_id={member_id}&status=pending",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert all(r["status"] == "pending" for r in data["data"])

    # Complete reminder
    resp = await api_context.request.patch(
        f"{BASE_URL}/api/reminders/{reminder_id}",
        headers=auth_headers,
        data=json.dumps({
            "status": "completed",
            "completed_date": "2024-08-01",
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert data["data"]["status"] == "completed"

    # Delete reminder
    resp = await api_context.request.delete(
        f"{BASE_URL}/api/reminders/{reminder_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"]["deleted"] is True


@pytest.mark.asyncio
async def test_api_health_timeline_flow_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create visit event
    resp = await api_context.request.post(
        f"{BASE_URL}/api/health-events",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "type": "visit",
            "event_date": "2024-06-15",
            "hospital": "协和医院",
            "department": "心内科",
            "doctor": "李医生",
            "diagnosis": "高血压",
            "notes": "开了降压药",
            "status": "abnormal",
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    event_id = data["data"]["id"]
    assert data["data"]["type"] == "visit"
    assert data["data"]["status"] == "abnormal"

    # Create milestone event
    resp = await api_context.request.post(
        f"{BASE_URL}/api/health-events",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "type": "milestone",
            "event_date": "2024-06-01",
            "notes": "第一次独立行走",
            "status": "normal",
        }),
    )
    assert resp.ok

    # List all events
    resp = await api_context.request.get(
        f"{BASE_URL}/api/health-events?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert len(data["data"]) >= 2

    # Filter by type
    resp = await api_context.request.get(
        f"{BASE_URL}/api/health-events?member_id={member_id}&type=milestone",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert all(e["type"] == "milestone" for e in data["data"])

    # Update event
    resp = await api_context.request.patch(
        f"{BASE_URL}/api/health-events/{event_id}",
        headers=auth_headers,
        data=json.dumps({
            "notes": "开了降压药，每日一片",
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert data["data"]["notes"] == "开了降压药，每日一片"

    # Delete event
    resp = await api_context.request.delete(
        f"{BASE_URL}/api/health-events/{event_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"]["deleted"] is True