from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class ReminderBase(BaseModel):
    type: str
    title: str
    description: str | None = None
    scheduled_date: date
    status: str = "pending"
    related_indicator: str | None = None
    related_report_id: str | None = None
    priority: str = "normal"

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("vaccine", "checkup", "review", "medication"):
            raise ValueError("type must be one of: vaccine, checkup, review, medication")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("pending", "completed", "overdue"):
            raise ValueError("status must be one of: pending, completed, overdue")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in ("critical", "high", "normal", "low"):
            raise ValueError("priority must be one of: critical, high, normal, low")
        return v


class ReminderCreate(ReminderBase):
    member_id: str


class ReminderUpdate(BaseModel):
    type: str | None = None
    title: str | None = None
    description: str | None = None
    scheduled_date: date | None = None
    status: str | None = None
    completed_date: date | None = None
    related_indicator: str | None = None
    related_report_id: str | None = None
    priority: str | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in ("vaccine", "checkup", "review", "medication"):
            raise ValueError("type must be one of: vaccine, checkup, review, medication")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in ("pending", "completed", "overdue"):
            raise ValueError("status must be one of: pending, completed, overdue")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in ("critical", "high", "normal", "low"):
            raise ValueError("priority must be one of: critical, high, normal, low")
        return v


class ReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    member_id: str
    type: str
    title: str
    description: str | None
    scheduled_date: date
    status: str
    completed_date: date | None
    related_indicator: str | None
    related_report_id: str | None
    priority: str
    created_at: Any
