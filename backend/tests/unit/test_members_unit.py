"""Unit tests for members API endpoints that are hard to cover via integration tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.members import create_family
from app.schemas.member import MemberOut


class TestCreateFamilyUnit:
    async def test_create_family_success(self):
        """Cover create_family success path (unreachable in integration tests
        because DB schema does not allow family_id=NULL)."""
        mock_member = MagicMock()
        mock_member.family_id = None
        mock_member.id = "member-id"
        mock_member.name = "旧名字"
        mock_member.gender = "male"
        mock_member.type = "adult"
        mock_member.role = "member"
        mock_member.avatar_url = None
        mock_member.birth_date = None
        mock_member.blood_type = None
        mock_member.allergies = []
        mock_member.chronic_diseases = []
        mock_member.subscription_status = {}
        mock_member.created_at = MagicMock()

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_family_instance = MagicMock()
        mock_family_instance.id = "family-id"
        mock_family_instance.name = "新名字的家庭"
        mock_family_instance.invite_code = "ABC123"
        mock_family_instance.admin_id = None
        mock_family_instance.created_at = MagicMock()

        with patch("app.api.members.Family", return_value=mock_family_instance):
            result = await create_family(
                creator_name="新名字",
                member=mock_member,
                db=mock_db,
            )

        assert mock_member.family_id == "family-id"
        assert mock_member.role == "creator"
        assert mock_member.name == "新名字"
        assert mock_family_instance.admin_id == "member-id"
        assert isinstance(result.data, MemberOut)
        assert result.data.family_id == "family-id"
        assert result.data.role == "creator"

        mock_db.add.assert_called_once_with(mock_family_instance)
        mock_db.flush.assert_awaited_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(mock_member)
