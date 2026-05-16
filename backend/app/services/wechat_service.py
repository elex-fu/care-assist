"""WeChat MiniProgram subscription message service."""

import asyncio
import time
from typing import Optional

import httpx

from app.config import settings
from app.core.exceptions import BusinessException


class WeChatService:
    _access_token: Optional[str] = None
    _token_expires_at: float = 0.0
    _lock = asyncio.Lock()

    @classmethod
    async def get_access_token(cls) -> str:
        """Fetch and cache WeChat access token."""
        if cls._access_token and time.time() < cls._token_expires_at - 300:
            return cls._access_token

        async with cls._lock:
            # Double-check after acquiring lock
            if cls._access_token and time.time() < cls._token_expires_at - 300:
                return cls._access_token

            if not settings.WECHAT_APPID or not settings.WECHAT_SECRET:
                raise BusinessException(code=2001, message="微信 AppID 或 Secret 未配置")

            url = "https://api.weixin.qq.com/cgi-bin/token"
            params = {
                "grant_type": "client_credential",
                "appid": settings.WECHAT_APPID,
                "secret": settings.WECHAT_SECRET,
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                data = resp.json()

            if "access_token" not in data:
                raise BusinessException(code=2002, message=f"获取微信 access_token 失败: {data}")

            cls._access_token = data["access_token"]
            expires_in = data.get("expires_in", 7200)
            cls._token_expires_at = time.time() + expires_in
            return cls._access_token

    @classmethod
    async def send_subscribe_message(
        cls,
        openid: str,
        template_id: str,
        data: dict,
        page: Optional[str] = None,
    ) -> dict:
        """Send WeChat subscription message.

        Args:
            openid: User's WeChat openid
            template_id: Message template ID from WeChat MP admin
            data: Template data dict, e.g. {"thing1": {"value": "阿莫西林"}, "time2": {"value": "2024-06-01"}}
            page: Optional mini-program page path to open on tap
        """
        token = await cls.get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={token}"

        payload = {
            "touser": openid,
            "template_id": template_id,
            "data": data,
        }
        if page:
            payload["page"] = page

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            result = resp.json()

        if result.get("errcode") != 0:
            raise BusinessException(
                code=result.get("errcode", 2003),
                message=f"发送订阅消息失败: {result.get('errmsg', '未知错误')}",
            )

        return result

    @classmethod
    async def send_medication_reminder(
        cls,
        openid: str,
        medication_name: str,
        dosage: str,
        scheduled_time: str,
        member_name: str,
        template_id: Optional[str] = None,
    ) -> dict:
        """Send medication reminder subscription message.

        Uses a generic template structure compatible with common
        "用药提醒" templates on WeChat MP.
        """
        if template_id is None:
            # Default placeholder; admin must replace with real template ID
            template_id = " medication_reminder_template_id"

        data = {
            "thing1": {"value": member_name},           # 成员名称
            "thing2": {"value": medication_name},       # 药品名称
            "thing3": {"value": dosage},                # 服用剂量
            "time4": {"value": scheduled_time},         # 提醒时间
        }

        return await cls.send_subscribe_message(
            openid=openid,
            template_id=template_id,
            data=data,
            page="/pkg-medication/pages/medication/medication",
        )
