from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class HospitalEventBase(BaseModel):
    hospital: str
    department: str | None = None
    admission_date: date
    discharge_date: date | None = None
    diagnosis: str | None = None
    doctor: str | None = None
    key_nodes: list[dict[str, Any]] | None = None
    watch_indicators: list[str] | None = None

    @field_validator("discharge_date")
    @classmethod
    def discharge_after_admission(cls, v: date | None, info) -> date | None:
        if v is None:
            return v
        admission = info.data.get("admission_date")
        if admission and v < admission:
            raise ValueError("出院日期不能早于入院日期")
        return v


class HospitalEventCreate(HospitalEventBase):
    member_id: str


class HospitalEventUpdate(BaseModel):
    hospital: str | None = None
    department: str | None = None
    admission_date: date | None = None
    discharge_date: date | None = None
    diagnosis: str | None = None
    doctor: str | None = None
    key_nodes: list[dict[str, Any]] | None = None
    watch_indicators: list[str] | None = None
    status: str | None = None

    @field_validator("discharge_date")
    @classmethod
    def discharge_after_admission(cls, v: date | None, info) -> date | None:
        if v is None:
            return v
        admission = info.data.get("admission_date")
        if admission and v < admission:
            raise ValueError("出院日期不能早于入院日期")
        return v


class HospitalEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    member_id: str
    hospital: str
    department: str | None
    admission_date: date
    discharge_date: date | None
    diagnosis: str | None
    doctor: str | None
    key_nodes: list[dict[str, Any]]
    watch_indicators: list[str]
    status: str
    created_at: Any
