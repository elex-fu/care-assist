"""Unit tests for permissions module."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.permissions import PermissionChecker, require_creator
from app.core.exceptions import ForbiddenException
from app.models.member import Member


class TestRequireCreator:
    async def test_require_creator_allows_creator(self):
        mock_member = MagicMock()
        mock_member.role = "creator"

        @require_creator()
        async def protected_func(member):
            return "success"

        result = await protected_func(member=mock_member)
        assert result == "success"

    async def test_require_creator_rejects_non_creator(self):
        mock_member = MagicMock()
        mock_member.role = "member"

        @require_creator()
        async def protected_func(member):
            return "success"

        with pytest.raises(ForbiddenException) as exc_info:
            await protected_func(member=mock_member)
        assert "仅家庭创建者可执行此操作" in str(exc_info.value)

    async def test_require_creator_rejects_missing_member(self):
        @require_creator()
        async def protected_func(member=None):
            return "success"

        with pytest.raises(ForbiddenException) as exc_info:
            await protected_func()
        assert "无法获取当前用户" in str(exc_info.value)


class TestPermissionCheckerIsCreator:
    def test_is_creator_true(self):
        member = MagicMock()
        member.role = "creator"
        assert PermissionChecker.is_creator(member) is True

    def test_is_creator_false(self):
        member = MagicMock()
        member.role = "member"
        assert PermissionChecker.is_creator(member) is False


class TestPermissionCheckerCanEditMember:
    def test_creator_can_edit_anyone(self):
        current = MagicMock()
        current.role = "creator"
        current.id = "creator-id"
        assert PermissionChecker.can_edit_member(current, "other-id") is True

    def test_member_can_edit_self(self):
        current = MagicMock()
        current.role = "member"
        current.id = "self-id"
        assert PermissionChecker.can_edit_member(current, "self-id") is True

    def test_member_cannot_edit_others(self):
        current = MagicMock()
        current.role = "member"
        current.id = "self-id"
        assert PermissionChecker.can_edit_member(current, "other-id") is False


class TestPermissionCheckerCanDeleteMember:
    def test_creator_can_delete_others(self):
        current = MagicMock()
        current.role = "creator"
        current.id = "creator-id"
        assert PermissionChecker.can_delete_member(current, "other-id") is True

    def test_creator_cannot_delete_self(self):
        current = MagicMock()
        current.role = "creator"
        current.id = "creator-id"
        assert PermissionChecker.can_delete_member(current, "creator-id") is False

    def test_non_creator_cannot_delete(self):
        current = MagicMock()
        current.role = "member"
        current.id = "member-id"
        assert PermissionChecker.can_delete_member(current, "other-id") is False
