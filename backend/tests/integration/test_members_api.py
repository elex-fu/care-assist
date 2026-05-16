"""Members API integration tests for uncovered endpoints."""

import uuid
from datetime import date

import pytest
from app.models.member import Member
from app.models.family import Family
from app.models.indicator import IndicatorData
from app.models.report import Report
from app.core.security import create_jwt
from decimal import Decimal


class TestUpdateSubscription:
    async def test_update_subscription_success(self, auth_client, test_creator):
        res = await auth_client.put(
            "/api/members/me/subscription",
            json={"daily_digest": True, "urgent_alert": False},
        )
        assert res.status_code == 200
        data = res.json()["data"]["subscription_status"]
        assert data["daily_digest"] is True
        assert data["urgent_alert"] is False

    async def test_update_subscription_partial(self, auth_client, test_creator):
        res = await auth_client.put(
            "/api/members/me/subscription",
            json={"review_reminder": True},
        )
        assert res.status_code == 200
        data = res.json()["data"]["subscription_status"]
        assert data["review_reminder"] is True


class TestCreateMember:
    async def test_create_member_as_creator(self, auth_client, test_family):
        res = await auth_client.post(
            "/api/members",
            params={"name": "新成员", "gender": "female", "type": "child"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["name"] == "新成员"
        assert data["family_id"] == test_family.id
        assert data["role"] == "member"

    async def test_create_member_as_non_creator_403(self, member_client):
        res = await member_client.post(
            "/api/members",
            params={"name": "新成员"},
        )
        assert res.status_code == 403


class TestListFamilyMembers:
    async def test_list_family_members(self, auth_client, test_creator, test_member):
        res = await auth_client.get("/api/members")
        assert res.status_code == 200
        data = res.json()["data"]
        assert "family" in data
        assert "members" in data
        member_ids = {m["id"] for m in data["members"]}
        assert test_creator.id in member_ids
        assert test_member.id in member_ids


class TestCreateFamily:
    @pytest.mark.skip(reason="DB schema does not allow family_id=NULL; success path unreachable via integration test")
    async def test_create_family_success(self, client, db):
        """Create a new family for a member without one.

        Note: This test is skipped because the members table has
        family_id NOT NULL, so no member can ever have family_id=None
        in the database. The endpoint's success path is effectively
        dead code under the current schema.
        """
        pass

    async def test_create_family_already_in_family_409(self, auth_client, test_creator):
        res = await auth_client.post(
            "/api/members/family",
            params={"creator_name": "测试创建者"},
        )
        assert res.status_code == 409


class TestGenerateInvite:
    async def test_generate_invite_as_creator(self, auth_client):
        res = await auth_client.post("/api/members/invite")
        assert res.status_code == 200
        data = res.json()["data"]
        assert "invite_link" in data
        assert data["invite_link"].startswith("/join?token=")
        assert data["expires_at"] == "7d"

    async def test_generate_invite_as_non_creator_403(self, member_client):
        res = await member_client.post("/api/members/invite")
        assert res.status_code == 403


class TestJoinFamily:
    async def test_join_family_success(self, auth_client, client, db):
        # Generate invite token as creator
        res = await auth_client.post("/api/members/invite")
        assert res.status_code == 200
        invite_link = res.json()["data"]["invite_link"]
        token = invite_link.split("token=")[1]

        # Join with a new client (no auth needed for join)
        res = await client.post(
            "/api/members/join",
            params={"token": token, "name": "新加入成员"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["name"] == "新加入成员"
        assert data["role"] == "member"

    async def test_join_family_invalid_token(self, client):
        res = await client.post(
            "/api/members/join",
            params={"token": "invalid_token", "name": "黑客"},
        )
        assert res.status_code == 403

    async def test_join_family_expired_or_bad_token(self, client):
        # Use an access token instead of invite token
        bad_token = create_jwt("some_member_id", token_type="access")
        res = await client.post(
            "/api/members/join",
            params={"token": bad_token, "name": "黑客"},
        )
        assert res.status_code == 403


class TestDeleteMember:
    async def test_delete_member_as_creator(self, auth_client, db, test_family):
        # Create a member to delete
        target = Member(
            id=str(uuid.uuid4()),
            family_id=test_family.id,
            name="待删除成员",
            gender="male",
            type="adult",
            role="member",
            wx_openid=f"mock_openid_{uuid.uuid4().hex[:16]}",
        )
        db.add(target)
        await db.commit()

        res = await auth_client.delete(f"/api/members/{target.id}")
        assert res.status_code == 200
        assert res.json()["data"]["deleted"] is True

    async def test_delete_self_403(self, auth_client, test_creator):
        res = await auth_client.delete(f"/api/members/{test_creator.id}")
        assert res.status_code == 403

    async def test_delete_member_not_found(self, auth_client):
        res = await auth_client.delete("/api/members/nonexistent-id")
        assert res.status_code == 404

    async def test_delete_member_as_non_creator_403(self, member_client, test_creator):
        res = await member_client.delete(f"/api/members/{test_creator.id}")
        assert res.status_code == 403

    async def test_delete_member_other_family_403(self, auth_client, db):
        other_family = Family(
            id=str(uuid.uuid4()),
            name="其他家庭",
            invite_code="OTHER1",
        )
        db.add(other_family)
        await db.commit()

        other_member = Member(
            id=str(uuid.uuid4()),
            family_id=other_family.id,
            name="其他成员",
            gender="male",
            type="adult",
            role="member",
            wx_openid=f"mock_openid_{uuid.uuid4().hex[:16]}",
        )
        db.add(other_member)
        await db.commit()

        res = await auth_client.delete(f"/api/members/{other_member.id}")
        assert res.status_code == 403
