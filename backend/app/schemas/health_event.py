from datetime import date, time, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class HealthEventBase(BaseModel):
    type: str
    event_date: date
    event_time: time | None = None
    hospital: str | None = None
    department: str | None = None
    doctor: str | None = None
    diagnosis: str | None = None
    notes: str | None = None
    report_id: str | None = None
    hospital_id: str | None = None
    status: str = "normal"

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"visit", "lab", "medication", "symptom", "ai", "hospital", "vaccine", "checkup", "milestone"}
        if v not in allowed:
            raise ValueError(f"type must be one of: {allowed}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("normal", "abnormal"):
            raise ValueError("status must be one of: normal, abnormal")
        return v


class HealthEventCreate(HealthEventBase):
    member_id: str


class HealthEventUpdate(BaseModel):
    type: str | None = None
    event_date: date | None = None
    event_time: time | None = None
    hospital: str | None = None
    department: str | None = None
    doctor: str | None = None
    diagnosis: str | None = None
    notes: str | None = None
    report_id: str | None = None
    hospital_id: str | None = None
    status: str | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"visit", "lab", "medication", "symptom", "ai", "hospital", "vaccine", "checkup", "milestone"}
        if v not in allowed:
            raise ValueError(f"type must be one of: {allowed}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in ("normal", "abnormal"):
            raise ValueError("status must be one of: normal, abnormal")
        return v


class HealthEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    member_id: str
    type: str
    event_date: date
    event_time: time | None
    hospital: str | None
    department: str | None
    doctor: str | None
    diagnosis: str | None
    notes: str | None
    report_id: str | None
    hospital_id: str | None
    status: str
    abnormal_count: int
    created_at: Any
