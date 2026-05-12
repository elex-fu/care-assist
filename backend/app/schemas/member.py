from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict


class MemberBase(BaseModel):
    name: str
    birth_date: date | None = None
    gender: str
    blood_type: str | None = None
    allergies: list[str] = []
    chronic_diseases: list[str] = []
    type: str = "adult"


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    name: str | None = None
    avatar_url: str | None = None
    birth_date: date | None = None
    gender: str | None = None
    blood_type: str | None = None
    allergies: list[str] | None = None
    chronic_diseases: list[str] | None = None
    type: str | None = None


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    family_id: str
    name: str
    avatar_url: str | None
    birth_date: date | None
    gender: str
    blood_type: str | None
    allergies: list[str]
    chronic_diseases: list[str]
    type: str
    role: str
    subscription_status: dict[str, Any]
    created_at: Any


class FamilyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    admin_id: str | None
    invite_code: str | None
    created_at: Any


class FamilyMembersOut(BaseModel):
    family: FamilyOut
    members: list[MemberOut]


class SubscriptionUpdate(BaseModel):
    daily_digest: bool | None = None
    urgent_alert: bool | None = None
    review_reminder: bool | None = None
