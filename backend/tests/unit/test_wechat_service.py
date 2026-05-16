import pytest
from unittest.mock import AsyncMock, patch

from app.services.wechat_service import WeChatService
from app.core.exceptions import BusinessException


class TestWeChatService:
    async def test_get_access_token_not_configured(self):
        with patch("app.services.wechat_service.settings.WECHAT_APPID", ""), \
             patch("app.services.wechat_service.settings.WECHAT_SECRET", ""):
            with pytest.raises(BusinessException):
                await WeChatService.get_access_token()

    async def test_get_access_token_fetches_and_caches(self):
        mock_response = {"access_token": "token_123", "expires_in": 7200}
        with patch("app.services.wechat_service.settings.WECHAT_APPID", "wx_123"), \
             patch("app.services.wechat_service.settings.WECHAT_SECRET", "secret_456"), \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value.json = lambda: mock_response
            token = await WeChatService.get_access_token()
            assert token == "token_123"
            assert WeChatService._access_token == "token_123"
            # Second call should use cache
            token2 = await WeChatService.get_access_token()
            assert token2 == "token_123"
            assert mock_get.call_count == 1

        # Clean up class state
        WeChatService._access_token = None
        WeChatService._token_expires_at = 0.0

    async def test_send_subscribe_message_success(self):
        with patch("app.services.wechat_service.settings.WECHAT_APPID", "wx_123"), \
             patch("app.services.wechat_service.settings.WECHAT_SECRET", "secret_456"), \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_get.return_value.json = lambda: {"access_token": "token_123", "expires_in": 7200}
            mock_post.return_value.json = lambda: {"errcode": 0, "errmsg": "ok"}

            result = await WeChatService.send_subscribe_message(
                openid="openid_123",
                template_id="tmpl_456",
                data={"thing1": {"value": "test"}},
            )
            assert result["errcode"] == 0

        WeChatService._access_token = None
        WeChatService._token_expires_at = 0.0

    async def test_send_subscribe_message_failure(self):
        with patch("app.services.wechat_service.settings.WECHAT_APPID", "wx_123"), \
             patch("app.services.wechat_service.settings.WECHAT_SECRET", "secret_456"), \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_get.return_value.json = lambda: {"access_token": "token_123", "expires_in": 7200}
            mock_post.return_value.json = lambda: {"errcode": 43101, "errmsg": "user refuse to accept"}

            with pytest.raises(BusinessException) as exc:
                await WeChatService.send_subscribe_message(
                    openid="openid_123",
                    template_id="tmpl_456",
                    data={"thing1": {"value": "test"}},
                )
            assert exc.value.biz_code == 43101

        WeChatService._access_token = None
        WeChatService._token_expires_at = 0.0

    async def test_send_medication_reminder(self):
        with patch("app.services.wechat_service.settings.WECHAT_APPID", "wx_123"), \
             patch("app.services.wechat_service.settings.WECHAT_SECRET", "secret_456"), \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_get.return_value.json = lambda: {"access_token": "token_123", "expires_in": 7200}
            mock_post.return_value.json = lambda: {"errcode": 0, "errmsg": "ok"}

            result = await WeChatService.send_medication_reminder(
                openid="openid_123",
                medication_name="阿莫西林",
                dosage="1粒",
                scheduled_time="2024-06-01 08:00",
                member_name="爸爸",
                template_id="tmpl_med",
            )
            assert result["errcode"] == 0
            # Verify payload structure
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["touser"] == "openid_123"
            assert payload["template_id"] == "tmpl_med"
            assert payload["page"] == "/pkg-medication/pages/medication/medication"
            assert payload["data"]["thing2"]["value"] == "阿莫西林"

        WeChatService._access_token = None
        WeChatService._token_expires_at = 0.0
