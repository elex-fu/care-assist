from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ReportBase(BaseModel):
    type: str
    hospital: Optional[str] = None
    department: Optional[str] = None
    report_date: Optional[date] = None


class ReportCreate(ReportBase):
    member_id: str


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    member_id: str
    type: str
    hospital: Optional[str]
    department: Optional[str]
    report_date: Optional[date]
    images: list[str]
    extracted_indicators: Optional[list[dict]]
    ai_summary: Optional[str]
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
