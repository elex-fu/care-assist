import pytest
from datetime import date

from app.schemas.hospital import HospitalEventCreate, HospitalEventUpdate


class TestHospitalEventValidation:
    def test_create_valid_event(self):
        payload = {
            "member_id": "m1",
            "hospital": "测试医院",
            "department": "内科",
            "admission_date": "2024-06-01",
            "discharge_date": "2024-06-10",
            "diagnosis": "肺炎",
            "doctor": "张医生",
        }
        event = HospitalEventCreate.model_validate(payload)
        assert event.hospital == "测试医院"
        assert event.discharge_date == date(2024, 6, 10)

    def test_create_without_discharge_date(self):
        payload = {
            "member_id": "m1",
            "hospital": "测试医院",
            "admission_date": "2024-06-01",
        }
        event = HospitalEventCreate.model_validate(payload)
        assert event.discharge_date is None

    def test_discharge_before_admission_raises(self):
        payload = {
            "member_id": "m1",
            "hospital": "测试医院",
            "admission_date": "2024-06-10",
            "discharge_date": "2024-06-01",
        }
        with pytest.raises(ValueError) as exc_info:
            HospitalEventCreate.model_validate(payload)
        assert "出院日期不能早于入院日期" in str(exc_info.value)

    def test_update_discharge_before_admission_raises(self):
        payload = {
            "admission_date": "2024-06-10",
            "discharge_date": "2024-06-01",
        }
        with pytest.raises(ValueError) as exc_info:
            HospitalEventUpdate.model_validate(payload)
        assert "出院日期不能早于入院日期" in str(exc_info.value)

    def test_same_day_admission_discharge_ok(self):
        payload = {
            "member_id": "m1",
            "hospital": "测试医院",
            "admission_date": "2024-06-01",
            "discharge_date": "2024-06-01",
        }
        event = HospitalEventCreate.model_validate(payload)
        assert event.discharge_date == date(2024, 6, 1)

    def test_create_with_key_nodes_and_watch_indicators(self):
        payload = {
            "member_id": "m1",
            "hospital": "测试医院",
            "admission_date": "2024-06-01",
            "key_nodes": [
                {"date": "2024-06-01", "event": "入院", "notes": "急诊入院"},
                {"date": "2024-06-05", "event": "手术", "notes": "微创手术"},
            ],
            "watch_indicators": ["systolic_bp", "fasting_glucose"],
        }
        event = HospitalEventCreate.model_validate(payload)
        assert len(event.key_nodes) == 2
        assert event.watch_indicators == ["systolic_bp", "fasting_glucose"]
