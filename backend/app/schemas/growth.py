from datetime import date

from pydantic import BaseModel, ConfigDict


class GrowthRecordCreate(BaseModel):
    member_id: str
    record_type: str  # height / weight / head_circumference / bmi
    value: float
    unit: str
    recorded_at: date
    note: str | None = None


class GrowthRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    member_id: str
    record_type: str
    value: float
    unit: str
    recorded_at: date
    note: str | None
    age_months: int | None = None
    percentile: float | None = None
    z_score: float | None = None
    status: str | None = None
    assessment_label: str | None = None


class GrowthChartPoint(BaseModel):
    age_months: int
    p3: float
    p15: float
    p50: float
    p85: float
    p97: float


class GrowthChartOut(BaseModel):
    record_type: str
    unit: str
    records: list[GrowthRecordOut]
    percentile_curve: list[GrowthChartPoint]


class MilestoneItem(BaseModel):
    age_months: int
    title: str
    description: str
    category: str  # motor / language / cognitive / social
    is_completed: bool = False
    status: str = "normal"  # normal / warning / achieved / delayed
