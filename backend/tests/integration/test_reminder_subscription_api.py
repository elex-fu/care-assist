from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_get_reminder_template_ids(client):
    with patch(
        "app.api.reminders.settings.REMINDER_MEDICATION_TEMPLATE_ID", "tmpl_med_123"
    ), patch("app.api.reminders.settings.REMINDER_VACCINE_TEMPLATE_ID", "tmpl_vaccine_456"):
        res = await client.get("/api/reminders/template-ids")

    assert res.status_code == 200
    body = res.json()
    assert body["code"] == 0
    assert body["data"]["medication"] == "tmpl_med_123"
    assert body["data"]["vaccine"] == "tmpl_vaccine_456"
    assert body["data"]["checkup"] is None


@pytest.mark.asyncio
async def test_record_reminder_subscription(client, auth_client, test_creator):
    res = await auth_client.post(
        "/api/reminders/subscribe",
        json={"template_ids": ["tmpl_1", "tmpl_2", "tmpl_1"]},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["code"] == 0
    assert body["data"]["subscribed"] is True
