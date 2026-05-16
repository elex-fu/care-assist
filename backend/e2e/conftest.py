"""Shared Playwright fixtures for backend E2E tests."""

import json
import os
import uuid

import pytest_asyncio
from playwright.async_api import async_playwright


BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8000")


@pytest_asyncio.fixture(scope="session")
async def playwright_instance():
    async with async_playwright() as p:
        yield p


@pytest_asyncio.fixture(scope="session")
async def browser(playwright_instance):
    browser = await playwright_instance.chromium.launch(headless=True)
    yield browser
    await browser.close()


@pytest_asyncio.fixture(scope="session")
async def api_context(browser):
    context = await browser.new_context()
    yield context
    await context.close()


@pytest_asyncio.fixture(loop_scope="function")
async def registered_user(api_context):
    """Register a new user and return auth info."""
    code = f"mock_e2e_{uuid.uuid4().hex[:8]}"
    creator_name = f"E2E_{uuid.uuid4().hex[:6]}"

    resp = await api_context.request.post(
        f"{BASE_URL}/api/auth/register?creator_name={creator_name}",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"code": code}),
    )
    assert resp.ok, await resp.text()
    body = await resp.json()

    return {
        "token": body["data"]["access_token"],
        "member_id": body["data"]["member"]["id"],
        "family_id": body["data"]["member"].get("family_id"),
        "name": creator_name,
    }


@pytest_asyncio.fixture(loop_scope="function")
async def auth_headers(registered_user):
    return {
        "Authorization": f"Bearer {registered_user['token']}",
        "Content-Type": "application/json",
    }


@pytest_asyncio.fixture(loop_scope="function")
async def swagger_page(browser):
    """Provide a fresh browser page for Swagger UI screenshots."""
    page = await browser.new_page(viewport={"width": 1280, "height": 800})
    yield page
    await page.close()
