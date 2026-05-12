from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class VaccineRecordBase(BaseModel):
    vaccine_name: str
    dose: int = 1
    scheduled_date: date
    actual_date: date | None = None
    status: str = "pending"
    location: str | None = None
    batch_no: str | None = None
    reaction: str | None = None
    is_custom: bool = False

    @field_validator("dose")
    @classmethod
    def dose_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("剂次必须大于等于1")
        return v


class VaccineRecordCreate(VaccineRecordBase):
    member_id: str


class VaccineRecordUpdate(BaseModel):
    vaccine_name: str | None = None
    dose: int | None = None
    scheduled_date: date | None = None
    actual_date: date | None = None
    status: str | None = None
    location: str | None = None
    batch_no: str | None = None
    reaction: str | None = None
    is_custom: bool | None = None

    @field_validator("dose")
    @classmethod
    def dose_must_be_positive(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("剂次必须大于等于1")
        return v


class VaccineRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    member_id: str
    vaccine_name: str
    dose: int
    scheduled_date: date
    actual_date: date | None
    status: str
    location: str | None
    batch_no: str | None
    reaction: str | None
    is_custom: bool
    created_at: Any


class VaccineScheduleEntry(BaseModel):
    vaccine_name: str
    dose: int
    recommended_age_months: int
    scheduled_date: date
