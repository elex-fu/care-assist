from datetime import date

from pydantic import BaseModel


class ChronicIndicatorItem(BaseModel):
    key: str
    name: str
    value: float | None
    unit: str
    status: str
    ref_range: str | None


class ChronicPackageListItem(BaseModel):
    package: str
    name: str
    description: str


class ChronicPackageResponse(BaseModel):
    package: str
    name: str
    indicators: list[ChronicIndicatorItem]
    summary: str


class ChronicTrendPoint(BaseModel):
    value: float
    record_date: date
    status: str


class ChronicTrendSeries(BaseModel):
    indicator_key: str
    indicator_name: str
    unit: str
    points: list[ChronicTrendPoint]
    trend_direction: str


class ChronicTrendOut(BaseModel):
    package: str
    member_id: str
    series: list[ChronicTrendSeries]
