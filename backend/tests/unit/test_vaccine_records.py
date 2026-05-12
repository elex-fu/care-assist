from datetime import date

import pytest

from app.schemas.vaccine import VaccineRecordCreate, VaccineRecordUpdate


class TestVaccineRecordValidation:
    def test_create_valid_record(self):
        payload = {
            "member_id": "m1",
            "vaccine_name": "乙肝疫苗",
            "dose": 1,
            "scheduled_date": "2024-06-01",
            "status": "pending",
        }
        record = VaccineRecordCreate.model_validate(payload)
        assert record.vaccine_name == "乙肝疫苗"
        assert record.dose == 1

    def test_dose_must_be_positive(self):
        payload = {
            "member_id": "m1",
            "vaccine_name": "乙肝疫苗",
            "dose": 0,
            "scheduled_date": "2024-06-01",
        }
        with pytest.raises(ValueError) as exc_info:
            VaccineRecordCreate.model_validate(payload)
        assert "剂次必须大于等于1" in str(exc_info.value)

    def test_update_dose_must_be_positive(self):
        payload = {
            "dose": -1,
        }
        with pytest.raises(ValueError) as exc_info:
            VaccineRecordUpdate.model_validate(payload)
        assert "剂次必须大于等于1" in str(exc_info.value)

    def test_create_with_optional_fields(self):
        payload = {
            "member_id": "m1",
            "vaccine_name": "卡介苗",
            "dose": 1,
            "scheduled_date": "2024-06-01",
            "actual_date": "2024-06-01",
            "status": "completed",
            "location": "社区医院",
            "batch_no": "ABC123",
            "reaction": "无不良反应",
            "is_custom": False,
        }
        record = VaccineRecordCreate.model_validate(payload)
        assert record.actual_date == date(2024, 6, 1)
        assert record.location == "社区医院"

    def test_create_custom_vaccine(self):
        payload = {
            "member_id": "m1",
            "vaccine_name": "自费流感疫苗",
            "dose": 1,
            "scheduled_date": "2024-06-01",
            "is_custom": True,
        }
        record = VaccineRecordCreate.model_validate(payload)
        assert record.is_custom is True


class TestVaccineStatusLogic:
    def test_status_completed_with_actual_date(self):
        payload = {
            "member_id": "m1",
            "vaccine_name": "乙肝疫苗",
            "dose": 1,
            "scheduled_date": "2024-06-01",
            "actual_date": "2024-06-01",
            "status": "completed",
        }
        record = VaccineRecordCreate.model_validate(payload)
        assert record.status == "completed"

    def test_status_pending_without_actual_date(self):
        payload = {
            "member_id": "m1",
            "vaccine_name": "乙肝疫苗",
            "dose": 1,
            "scheduled_date": "2024-06-01",
            "status": "pending",
        }
        record = VaccineRecordCreate.model_validate(payload)
        assert record.status == "pending"
