from pydantic import BaseModel


class IndicatorMetadata(BaseModel):
    key: str
    name: str
    aliases: list[str]
    unit: str
    ref_range: str | None
