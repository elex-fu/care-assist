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
