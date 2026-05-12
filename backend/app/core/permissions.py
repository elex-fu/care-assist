from functools import wraps
from typing import Callable

from fastapi import Depends

from app.core.exceptions import ForbiddenException
from app.models.member import Member
from app.core.security import get_current_member


def require_creator(
    member_param: str = "member",
) -> Callable:
    """Decorator: require current member to be family creator."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            member: Member = kwargs.get(member_param)
            if not member:
                raise ForbiddenException("无法获取当前用户")
            if member.role != "creator":
                raise ForbiddenException("仅家庭创建者可执行此操作")
            return await func(*args, **kwargs)

        return wrapper

    return decorator


class PermissionChecker:
    @staticmethod
    def is_creator(member: Member) -> bool:
        return member.role == "creator"

    @staticmethod
    def can_edit_member(current: Member, target_member_id: str) -> bool:
        if current.role == "creator":
            return True
        return current.id == target_member_id

    @staticmethod
    def can_delete_member(current: Member, target_member_id: str) -> bool:
        if current.role != "creator":
            return False
        return current.id != target_member_id
