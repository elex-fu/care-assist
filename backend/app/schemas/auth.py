from pydantic import BaseModel

from app.schemas.member import MemberOut


class WechatLoginRequest(BaseModel):
    code: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    member: MemberOut


class RefreshTokenRequest(BaseModel):
    refresh_token: str
