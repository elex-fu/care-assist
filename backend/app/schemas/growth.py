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


class MilestoneItem(BaseModel):
    age_months: int
    title: str
    description: str
    category: str  # motor / language / cognitive / social
    is_completed: bool = False
