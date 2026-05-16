import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.auth import _get_wx_openid
from app.core.security import create_jwt, decode_jwt


class TestGetWxOpenid:
    async def test_mock_openid_in_dev(self):
        with patch("app.api.auth.settings.WECHAT_APPID", ""), \
             patch("app.api.auth.settings.WECHAT_SECRET", ""):
            openid = await _get_wx_openid("test_code_123")
            assert openid.startswith("mock_openid_")
            assert len(openid) == len("mock_openid_") + 16

    async def test_mock_openid_deterministic(self):
        with patch("app.api.auth.settings.WECHAT_APPID", ""), \
             patch("app.api.auth.settings.WECHAT_SECRET", ""):
            openid1 = await _get_wx_openid("same_code")
            openid2 = await _get_wx_openid("same_code")
            assert openid1 == openid2

    async def test_mock_openid_different_codes(self):
        with patch("app.api.auth.settings.WECHAT_APPID", ""), \
             patch("app.api.auth.settings.WECHAT_SECRET", ""):
            openid1 = await _get_wx_openid("code_a")
            openid2 = await _get_wx_openid("code_b")
            assert openid1 != openid2


class TestJWT:
    def test_create_and_decode_access_token(self):
        member_id = "test-member-id"
        token = create_jwt(member_id, token_type="access")
        payload = decode_jwt(token)
        assert payload["sub"] == member_id
        assert payload["type"] == "access"

    def test_create_and_decode_refresh_token(self):
        member_id = "test-member-id"
        token = create_jwt(member_id, token_type="refresh")
        payload = decode_jwt(token)
        assert payload["sub"] == member_id
        assert payload["type"] == "refresh"

    def test_decode_invalid_token_raises(self):
        with pytest.raises(Exception):
            decode_jwt("invalid.token.here")
