"""Core user journey E2E test: register -> upload -> OCR -> indicators -> AI -> search -> export."""

import json

import pytest

from e2e.conftest import BASE_URL


@pytest.mark.asyncio
async def test_core_path_upload_ocr_to_indicators(api_context, registered_user, auth_headers):
    """Full core path: upload report -> OCR -> verify indicators -> AI chat -> search -> export -> dashboard."""
    member_id = registered_user["member_id"]

    # 1. Upload a report with a fake image
    resp = await api_context.request.post(
        f"{BASE_URL}/api/reports",
        headers={"Authorization": f"Bearer {registered_user['token']}"},
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

    # 2. Trigger OCR
    resp = await api_context.request.post(
        f"{BASE_URL}/api/reports/{report_id}/ocr",
        headers=auth_headers,
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert data["data"]["ocr_status"] == "completed"
    assert len(data["data"]["extracted"]) > 0
    extracted_keys = {item["indicator_key"] for item in data["data"]["extracted"]}
    assert "systolic_bp" in extracted_keys

    # 3. Verify indicators were created and are queryable
    resp = await api_context.request.get(
        f"{BASE_URL}/api/indicators?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert len(data["data"]) >= 1
    indicator_keys = {item["indicator_key"] for item in data["data"]}
    assert "systolic_bp" in indicator_keys

    # 4. Verify trend endpoint works for the extracted indicator
    resp = await api_context.request.get(
        f"{BASE_URL}/api/indicators/trend?member_id={member_id}&indicator_key=systolic_bp",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert "trend" in data["data"]

    # 5. AI conversation should reference the newly created indicator
    resp = await api_context.request.post(
        f"{BASE_URL}/api/ai-conversations",
        headers=auth_headers,
        data=json.dumps({"member_id": member_id, "page_context": "report"}),
    )
    assert resp.ok
    conv_id = (await resp.json())["data"]["id"]

    resp = await api_context.request.post(
        f"{BASE_URL}/api/ai-conversations/{conv_id}/messages",
        headers=auth_headers,
        data=json.dumps({"user_message": "我的血压怎么样"}),
    )
    assert resp.ok
    reply = (await resp.json())["data"]["reply"]
    # Should reference the actual data, not say "还没有记录"
    assert "还没有记录" not in reply

    # 6. Search should find the new indicator
    resp = await api_context.request.get(
        f"{BASE_URL}/api/search?q=收缩压&member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert any(r["entity_type"] == "indicator" for r in data["data"])

    # 7. Export member data should include the OCR-derived indicators
    resp = await api_context.request.get(
        f"{BASE_URL}/api/members/{member_id}/export",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert len(data["data"]["indicators"]) >= 1
    assert data["data"]["member"]["name"] == registered_user["name"]

    # 8. Dashboard should reflect the new member with indicators
    resp = await api_context.request.get(
        f"{BASE_URL}/api/home/dashboard",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    members = data["data"]["members"]
    assert any(m["id"] == member_id for m in members)
    member_card = next(m for m in members if m["id"] == member_id)
    assert "latest_indicators" in member_card
    assert len(member_card["latest_indicators"]) >= 1
