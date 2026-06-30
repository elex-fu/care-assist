"""Push notification service for reminders."""

from app.config import settings
from app.core.logging import get_logger
from app.models.member import Member
from app.models.reminder import Reminder
from app.services.wechat_service import WeChatService

logger = get_logger("app.services.notification_service")


class NotificationService:
    """Send WeChat subscription messages when reminders are generated."""

    _PAGE_MAP = {
        "medication": "/pkg-medication/pages/medication/medication",
        "vaccine": "/pkg-child/pages/vaccine/vaccine",
        "checkup": "/pages/home/home",
        "review": "/pages/reports/reports",
    }

    @staticmethod
    def _template_id(reminder_type: str) -> str | None:
        mapping = {
            "medication": settings.REMINDER_MEDICATION_TEMPLATE_ID,
            "vaccine": settings.REMINDER_VACCINE_TEMPLATE_ID,
            "checkup": settings.REMINDER_CHECKUP_TEMPLATE_ID,
            "review": settings.REMINDER_REVIEW_TEMPLATE_ID,
        }
        return mapping.get(reminder_type)

    @staticmethod
    def _truncate(value: str, max_length: int) -> str:
        value = value or ""
        if len(value) <= max_length:
            return value
        return value[: max_length - 1] + "…"

    @classmethod
    def _build_data(cls, reminder: Reminder, member: Member) -> dict:
        title = cls._truncate(reminder.title, 20)
        name = cls._truncate(member.name, 20)
        scheduled = str(reminder.scheduled_date)
        description = cls._truncate(reminder.description or "", 20)

        # Generic structure that fits most WeChat "提醒" templates:
        # thing1: 标题, time2: 计划时间, thing3: 成员/备注, thing4: 描述
        if reminder.type == "medication":
            return {
                "thing1": {"value": title},
                "time2": {"value": scheduled},
                "thing3": {"value": name},
                "thing4": {"value": description},
            }
        if reminder.type == "vaccine":
            return {
                "thing1": {"value": title},
                "time2": {"value": scheduled},
                "thing3": {"value": name},
                "thing4": {"value": description},
            }
        return {
            "thing1": {"value": title},
            "time2": {"value": scheduled},
            "thing3": {"value": name},
            "thing4": {"value": description},
        }

    @classmethod
    async def send_reminder(cls, reminder: Reminder, member: Member) -> dict | None:
        """Best-effort send a WeChat subscription message for a reminder.

        Returns the WeChat API result when a push is attempted, or None when
        the member has no openid / no template is configured.
        Push failures are swallowed and logged so they never break the main flow.
        """
        if not member or not member.wx_openid:
            logger.debug(f"Skip push for reminder {reminder.id}: member has no openid")
            return None

        template_id = cls._template_id(reminder.type)
        if not template_id:
            logger.debug(f"Skip push for reminder {reminder.id}: no template configured")
            return None

        data = cls._build_data(reminder, member)
        page = cls._PAGE_MAP.get(reminder.type)

        try:
            result = await WeChatService.send_subscribe_message(
                openid=member.wx_openid,
                template_id=template_id,
                data=data,
                page=page,
            )
            logger.info(f"Push sent for reminder {reminder.id}: {result.get('errcode')}")
            return result
        except Exception as exc:
            logger.warning(f"Push failed for reminder {reminder.id}: {exc}")
            return None
