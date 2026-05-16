from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class MedicationBase(BaseModel):
    name: str
    dosage: str
    frequency: str
    time_slots: list[str]
    start_date: date
    end_date: date | None = None
    notes: str | None = None
    status: str = "active"

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("active", "paused", "completed"):
            raise ValueError("status must be one of: active, paused, completed")
        return v


class MedicationCreate(MedicationBase):
    member_id: str


class MedicationUpdate(BaseModel):
    name: str | None = None
    dosage: str | None = None
    frequency: str | None = None
    time_slots: list[str] | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in ("active", "paused", "completed"):
            raise ValueError("status must be one of: active, paused, completed")
        return v


class MedicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    member_id: str
    name: str
    dosage: str
    frequency: str
    time_slots: list[str]
    start_date: date
    end_date: date | None
    notes: str | None
    status: str
    created_at: Any
    updated_at: Any


class MedicationLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    medication_id: str
    member_id: str
    scheduled_date: date
    scheduled_time: str
    taken_at: datetime | None
    status: str
    notes: str | None
    created_at: Any


class MedicationTakeRequest(BaseModel):
    scheduled_date: date
    scheduled_time: str
    notes: str | None = None


class MedicationWithLogsOut(BaseModel):
    medication: MedicationOut
    logs: list[MedicationLogOut]
    adherence_rate: float
