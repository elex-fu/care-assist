from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict


class ReportBase(BaseModel):
    type: str
    hospital: str | None = None
    department: str | None = None
    report_date: date | None = None


class ReportCreate(ReportBase):
    member_id: str


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    member_id: str
    type: str
    hospital: str | None
    department: str | None
    report_date: date | None
    images: list[str]
    extracted_indicators: list[dict] | None
    ai_summary: str | None
    ocr_status: str
    created_at: Any


class ReportListOut(BaseModel):
    reports: list[ReportOut]


class OCRResultItem(BaseModel):
    indicator_key: str
    indicator_name: str
    value: float
    unit: str
    raw_text: str


class OCRTriggerOut(BaseModel):
    report_id: str
    ocr_status: str
    extracted: list[OCRResultItem]
    ai_summary: str | None = None


class ReportAISummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ai_summary: str | None
    updated_at: Any
