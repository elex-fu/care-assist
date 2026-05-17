import httpx
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.core.security import create_jwt, decode_jwt, get_db
from app.core.exceptions import UnauthorizedException, NotFoundException
from app.core.logging import get_logger
from app.models.member import Member
from app.models.family import Family
from app.schemas.auth import WechatLoginRequest, TokenResponse, RefreshTokenRequest
from app.schemas.common import ResponseWrapper
from app.schemas.member import MemberOut

router = APIRouter(prefix="/auth", tags=["认证"])
logger = get_logger("app.api.auth")


async def _get_wx_openid(code: str) -> str:
    """Call WeChat jscode2session or mock in dev."""
    if not settings.WECHAT_APPID or not settings.WECHAT_SECRET:
        # Dev mock: deterministic openid from code hash
        import hashlib
        openid = f"mock_openid_{hashlib.sha256(code.encode()).hexdigest()[:16]}"
        logger.debug(f"Dev mock openid generated: {openid[:16]}...")
        return openid

    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.WECHAT_APPID,
        "secret": settings.WECHAT_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    logger.info("Calling WeChat jscode2session API")
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        data = resp.json()

    if "openid" not in data:
        logger.warning(f"WeChat login failed: {data.get('errmsg', '未知错误')}")
        raise UnauthorizedException(f"微信登录失败: {data.get('errmsg', '未知错误')}")

    logger.info(f"WeChat openid obtained successfully")
    return data["openid"]


@router.post("/login", response_model=ResponseWrapper[TokenResponse])
async def wechat_login(
    req: WechatLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    openid = await _get_wx_openid(req.code)

    result = await db.execute(select(Member).where(Member.wx_openid == openid))
    member = result.scalar_one_or_none()

    if not member:
        logger.warning(f"Login failed: member not found for openid {openid[:8]}...")
        raise NotFoundException("用户未注册，请先创建家庭")

    access_token = create_jwt(str(member.id), token_type="access")
    refresh_token = create_jwt(str(member.id), token_type="refresh")

    logger.info(f"Member logged in: id={member.id} name={member.name}")
    return ResponseWrapper(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            member=MemberOut.model_validate(member),
        )
    )


@router.post("/register", response_model=ResponseWrapper[TokenResponse])
async def wechat_register(
    req: WechatLoginRequest,
    creator_name: str,
    db: AsyncSession = Depends(get_db),
):
    """First-time user: create family + member, then login."""
    openid = await _get_wx_openid(req.code)

    # Check if already exists
    result = await db.execute(select(Member).where(Member.wx_openid == openid))
    if result.scalar_one_or_none():
        logger.warning(f"Register failed: member already exists for openid {openid[:8]}...")
        raise UnauthorizedException("用户已存在，请直接登录")

    # Create family
    import secrets
    import uuid

    family = Family(
        id=str(uuid.uuid4()),
        name=f"{creator_name}的家庭",
        invite_code=secrets.token_urlsafe(8)[:6].upper(),
    )
    db.add(family)
    await db.flush()

    # Create member as creator
    member = Member(
        id=str(uuid.uuid4()),
        family_id=family.id,
        name=creator_name,
        gender="male",
        role="creator",
        wx_openid=openid,
    )
    db.add(member)
    await db.flush()

    # Update family admin_id
    family.admin_id = member.id
    await db.commit()
    await db.refresh(member)

    logger.info(f"New member registered: id={member.id} name={member.name} family_id={family.id}")

    access_token = create_jwt(str(member.id), token_type="access")
    refresh_token = create_jwt(str(member.id), token_type="refresh")

    return ResponseWrapper(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            member=MemberOut.model_validate(member),
        )
    )


@router.post("/refresh", response_model=ResponseWrapper[dict])
async def refresh_token(
    req: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    payload = decode_jwt(req.refresh_token)

    if payload.get("type") != "refresh":
        logger.warning("Refresh token failed: invalid token type")
        raise UnauthorizedException("Token 类型错误")

    member_id = payload.get("sub")
    result = await db.execute(select(Member).where(Member.id == member_id))
    member = result.scalar_one_or_none()
    if not member:
        logger.warning(f"Refresh token failed: member not found id={member_id}")
        raise UnauthorizedException("用户不存在")

    access_token = create_jwt(str(member.id), token_type="access")
    logger.info(f"Token refreshed for member_id={member.id}")

    return ResponseWrapper(
        data={
            "access_token": access_token,
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }
    )
