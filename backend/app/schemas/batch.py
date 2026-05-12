from datetime import date, time

from pydantic import BaseModel


class BatchIndicatorItem(BaseModel):
    indicator_key: str
    indicator_name: str
    value: float
    unit: str
    record_date: date
    record_time: time | None = None
    source_report_id: str | None = None
    source_hospital_id: str | None = None
    source_batch_id: str | None = None


class BatchIndicatorCreate(BaseModel):
    member_id: str
    items: list[BatchIndicatorItem]
