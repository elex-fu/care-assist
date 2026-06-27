from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.medication import MedicationLogCreate


def test_medication_log_create_valid():
    data = {
        "medication_id": "med-001",
        "member_id": "member-001",
        "scheduled_date": date(2024, 1, 1),
        "scheduled_time": "08:00",
        "status": "pending",
        "notes": "Take with food",
    }
    log = MedicationLogCreate(**data)
    assert log.medication_id == "med-001"
    assert log.member_id == "member-001"
    assert log.scheduled_date == date(2024, 1, 1)
    assert log.scheduled_time == "08:00"
    assert log.status == "pending"
    assert log.notes == "Take with food"


def test_medication_log_create_default_status_and_notes():
    data = {
        "medication_id": "med-002",
        "member_id": "member-002",
        "scheduled_date": date(2024, 1, 2),
        "scheduled_time": "09:00",
    }
    log = MedicationLogCreate(**data)
    assert log.status == "pending"
    assert log.notes is None


@pytest.mark.parametrize("status", ["pending", "taken", "missed", "skipped"])
def test_medication_log_create_valid_status(status):
    data = {
        "medication_id": "med-003",
        "member_id": "member-003",
        "scheduled_date": date(2024, 1, 3),
        "scheduled_time": "10:00",
        "status": status,
    }
    log = MedicationLogCreate(**data)
    assert log.status == status


def test_medication_log_create_invalid_status():
    data = {
        "medication_id": "med-004",
        "member_id": "member-004",
        "scheduled_date": date(2024, 1, 4),
        "scheduled_time": "11:00",
        "status": "unknown",
    }
    with pytest.raises(ValidationError) as exc_info:
        MedicationLogCreate(**data)
    assert "status" in str(exc_info.value)
