import json

from e2e.conftest import BASE_URL


async def test_swagger_docs_show_members(swagger_page):
    resp = await swagger_page.request.get(f"{BASE_URL}/openapi.json")
    assert resp.ok
    spec = await resp.json()
    paths = spec.get("paths", {})
    assert "/api/members/me" in paths
    assert "/api/members/{member_id}/export" in paths

    await swagger_page.goto(f"{BASE_URL}/docs")
    await swagger_page.wait_for_load_state("domcontentloaded")
    await swagger_page.wait_for_timeout(1000)
    await swagger_page.screenshot(path="e2e/screenshots/swagger_members.png", full_page=False)


async def test_api_member_export_flow_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create an indicator
    resp = await api_context.request.post(
        f"{BASE_URL}/api/indicators",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "indicator_key": "systolic_bp",
            "indicator_name": "收缩压",
            "value": 120.0,
            "unit": "mmHg",
            "record_date": "2024-06-15",
        }),
    )
    assert resp.ok

    # Export member health data
    resp = await api_context.request.get(
        f"{BASE_URL}/api/members/{member_id}/export",
        headers=auth_headers,
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert "member" in data["data"]
    assert len(data["data"]["indicators"]) >= 1
    assert data["data"]["member"]["name"] == registered_user["name"]
