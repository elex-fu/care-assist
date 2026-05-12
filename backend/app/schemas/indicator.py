from datetime import date, time, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class IndicatorBase(BaseModel):
    indicator_key: str
    indicator_name: str
    value: float
    unit: str
    record_date: date
    record_time: time | None = None
    source_report_id: str | None = None
    source_hospital_id: str | None = None
    source_batch_id: str | None = None


class IndicatorCreate(IndicatorBase):
    member_id: str


class IndicatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    member_id: str
    indicator_key: str
    indicator_name: str
    value: float
    unit: str
    lower_limit: float | None
    upper_limit: float | None
    status: str
    deviation_percent: float
    record_date: date
    record_time: time | None
    source_report_id: str | None
    source_hospital_id: str | None
    source_batch_id: str | None
    created_at: Any


class IndicatorTrendPoint(BaseModel):
    value: float
    record_date: date
    record_time: time | None
    status: str


class IndicatorTrendOut(BaseModel):
    indicator_key: str
    indicator_name: str
    unit: str
    current: IndicatorTrendPoint | None
    previous: IndicatorTrendPoint | None
    trend: dict[str, Any]
