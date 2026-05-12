import pytest
from datetime import date

from app.schemas.reminder import ReminderCreate, ReminderUpdate


class TestReminderValidation:
    def test_create_valid_reminder(self):
        payload = {
            "member_id": "m1",
            "type": "checkup",
            "title": "年度体检",
            "scheduled_date": "2024-06-01",
            "status": "pending",
            "priority": "high",
        }
        r = ReminderCreate.model_validate(payload)
        assert r.type == "checkup"
        assert r.priority == "high"

    def test_invalid_type_raises(self):
        payload = {
            "member_id": "m1",
            "type": "invalid",
            "title": "测试",
            "scheduled_date": "2024-06-01",
        }
        with pytest.raises(ValueError) as exc_info:
            ReminderCreate.model_validate(payload)
        assert "type must be one of" in str(exc_info.value)

    def test_invalid_status_raises(self):
        payload = {
            "member_id": "m1",
            "type": "vaccine",
            "title": "疫苗",
            "scheduled_date": "2024-06-01",
            "status": "unknown",
        }
        with pytest.raises(ValueError) as exc_info:
            ReminderCreate.model_validate(payload)
        assert "status must be one of" in str(exc_info.value)

    def test_invalid_priority_raises(self):
        payload = {
            "member_id": "m1",
            "type": "medication",
            "title": "服药",
            "scheduled_date": "2024-06-01",
            "priority": "urgent",
        }
        with pytest.raises(ValueError) as exc_info:
            ReminderCreate.model_validate(payload)
        assert "priority must be one of" in str(exc_info.value)

    def test_update_valid_fields(self):
        payload = {"status": "completed", "completed_date": "2024-06-01"}
        r = ReminderUpdate.model_validate(payload)
        assert r.status == "completed"
        assert r.completed_date == date(2024, 6, 1)
