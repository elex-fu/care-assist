import asyncio
import pytest
from app.core.security import create_jwt


class TestRefreshTokenRaceCondition:
    """Simulate frontend Promise lock scenario: 3 concurrent 401s should result
    in 1 refresh call on frontend, but backend must handle concurrent refresh safely.
    """

    async def test_concurrent_refresh_all_succeed(self, client, test_creator):
        """3 concurrent /auth/refresh calls with same refresh token all succeed."""
        refresh_token = create_jwt(str(test_creator.id), token_type="refresh")

        async def refresh():
            return await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})

        responses = await asyncio.gather(refresh(), refresh(), refresh())

        for resp in responses:
            assert resp.status_code == 200
            assert resp.json()["code"] == 0
            assert "access_token" in resp.json()["data"]

    async def test_refreshed_tokens_are_usable(self, client, test_creator):
        """Tokens returned from concurrent refresh can access protected endpoints."""
        refresh_token = create_jwt(str(test_creator.id), token_type="refresh")

        async def refresh_and_verify():
            resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
            data = resp.json()["data"]
            access_token = data["access_token"]

            # Use new token to access protected endpoint
            headers = {"Authorization": f"Bearer {access_token}"}
            me_resp = await client.get("/api/members/me", headers=headers)
            assert me_resp.status_code == 200
            assert me_resp.json()["data"]["id"] == str(test_creator.id)
            return True

        results = await asyncio.gather(refresh_and_verify(), refresh_and_verify(), refresh_and_verify())
        assert all(results)

    async def test_expired_refresh_token_rejected(self, client, test_creator):
        """Expired refresh token returns 401."""
        from datetime import timedelta

        expired_token = create_jwt(
            str(test_creator.id),
            token_type="refresh",
            expires_delta=timedelta(seconds=-1),
        )
        resp = await client.post("/api/auth/refresh", json={"refresh_token": expired_token})
        assert resp.status_code == 401

    async def test_access_token_cannot_refresh(self, client, test_creator):
        """Access token used as refresh token returns 401."""
        access_token = create_jwt(str(test_creator.id), token_type="access")
        resp = await client.post("/api/auth/refresh", json={"refresh_token": access_token})
        assert resp.status_code == 401
