from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from fastapi import Depends, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.core.exceptions import UnauthorizedException
from app.db.session import async_session
from app.models.member import Member

security_bearer = HTTPBearer(auto_error=False)


def create_jwt(
    subject: str,
    token_type: str = "access",
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None,
) -> str:
    if expires_delta is None:
        if token_type == "refresh":
            expires_delta = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
        else:
            expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError as exc:
        raise UnauthorizedException("Token 无效或已过期") from exc


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def get_current_member(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> Member:
    if not credentials:
        raise UnauthorizedException("缺少认证信息")

    token = credentials.credentials
    payload = decode_jwt(token)

    if payload.get("type") != "access":
        raise UnauthorizedException("Token 类型错误")

    member_id = payload.get("sub")
    if not member_id:
        raise UnauthorizedException("Token 内容无效")

    result = await db.execute(select(Member).where(Member.id == member_id))
    member = result.scalar_one_or_none()
    if not member:
        raise UnauthorizedException("用户不存在")

    return member
