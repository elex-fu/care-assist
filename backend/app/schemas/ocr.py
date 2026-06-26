from pydantic import BaseModel


class OCRResultItem(BaseModel):
    indicator_key: str
    indicator_name: str
    value: float
    unit: str
    raw_text: str = ""


class OCRPipelineResult(BaseModel):
    extracted: list[OCRResultItem]
    raw_text: str
    provider: str
