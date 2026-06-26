from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MatrixCell(BaseModel):
    value: Decimal
    status: str
    indicator_id: str

    model_config = ConfigDict(json_schema_extra={"example": {"value": 120, "status": "normal", "indicator_id": "1"}})


class IndicatorMatrixResponse(BaseModel):
    dates: list[str]
    indicator_keys: list[str]
    indicator_names: dict[str, str]
    units: dict[str, str]
    cells: dict[str, dict[str, Optional[MatrixCell]]]
