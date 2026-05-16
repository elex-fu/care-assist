"""End-to-end auth flow integration tests."""

from app.models.member import Member
from app.models.family import Family


class TestAuthFlow:
    async def test_register_creates_family_and_member(self, client):
        """First-time user registers and gets JWT."""
        res = await client.post(
            "/api/auth/register",
            params={"creator_name": "测试创建者"},
            json={"code": "mock_code_register_001"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["member"]["name"] == "测试创建者"
        assert data["member"]["role"] == "creator"

    async def test_login_existing_member(self, client, test_creator):
        """Existing member logs in with matching mock openid."""
        # test_creator has a mock_openid like "mock_openid_xxxx"
        # The auth endpoint hashes the code to generate openid in dev mode
        # So we need to use a code that produces the same openid
        # Actually easier: use the test_creator's openid directly by mocking
        from unittest.mock import patch

        with patch("app.api.auth._get_wx_openid", return_value=test_creator.wx_openid):
            res = await client.post("/api/auth/login", json={"code": "any_code"})
            assert res.status_code == 200
            data = res.json()["data"]
            assert "access_token" in data
            assert data["member"]["id"] == test_creator.id

    async def test_login_nonexistent_user_returns_404(self, client):
        """Login with unknown openid returns 404."""
        from unittest.mock import patch

        with patch("app.api.auth._get_wx_openid", return_value="unknown_openid_12345"):
            res = await client.post("/api/auth/login", json={"code": "unknown"})
            assert res.status_code == 404

    async def test_refresh_token_success(self, client, test_creator):
        from app.core.security import create_jwt

        refresh_token = create_jwt(str(test_creator.id), token_type="refresh")
        res = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert res.status_code == 200
        data = res.json()["data"]
        assert "access_token" in data
        assert "expires_in" in data

    async def test_get_me_requires_auth(self, client):
        """GET /api/members/me without token returns 401."""
        res = await client.get("/api/members/me")
        assert res.status_code == 401

    async def test_get_me_returns_current_member(self, auth_client, test_creator):
        """Authenticated user sees their own info."""
        res = await auth_client.get("/api/members/me")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["id"] == test_creator.id
        assert data["name"] == test_creator.name

    async def test_register_duplicate_returns_401(self, client, test_creator):
        """Register with existing openid returns error."""
        from unittest.mock import patch

        with patch("app.api.auth._get_wx_openid", return_value=test_creator.wx_openid):
            res = await client.post(
                "/api/auth/register",
                params={"creator_name": "重复用户"},
                json={"code": "any_code"},
            )
            assert res.status_code == 401

    async def test_update_me(self, auth_client, test_creator, db):
        """User can update their profile."""
        res = await auth_client.put("/api/members/me", json={"name": "新名字", "blood_type": "A"})
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["name"] == "新名字"
        assert data["blood_type"] == "A"
