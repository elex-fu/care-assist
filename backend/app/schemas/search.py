from datetime import date as dt_date
from typing import Any, Optional

from pydantic import BaseModel


class SearchResultItem(BaseModel):
    entity_type: str
    id: str
    member_id: str
    member_name: str
    title: str
    subtitle: Optional[str] = None
    record_date: Optional[dt_date] = None
    status: Optional[str] = None
    url: Optional[str] = None
    data: Optional[dict[str, Any]] = None


class SearchQuery(BaseModel):
    member_id: Optional[str] = None
    q: str
    entity_types: Optional[list[str]] = None
    limit: int = 20
