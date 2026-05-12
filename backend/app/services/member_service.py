from datetime import date, timedelta
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.member import Member
from app.models.indicator import IndicatorData
from app.models.family import Family


class MemberService:
    @staticmethod
    async def get_family_members(db: AsyncSession, family_id: str) -> Sequence[Member]:
        result = await db.execute(select(Member).where(Member.family_id == family_id))
        return result.scalars().all()

    @staticmethod
    async def get_member_dashboard(
        db: AsyncSession,
        member_id: str,
    ) -> dict:
        """Return aggregated dashboard data for a single member card."""
        # Latest indicators: one per indicator_key
        subq = (
            select(
                IndicatorData.indicator_key,
                func.max(IndicatorData.record_date).label("latest_date"),
            )
            .where(IndicatorData.member_id == member_id)
            .group_by(IndicatorData.indicator_key)
            .subquery()
        )

        latest_result = await db.execute(
            select(IndicatorData)
            .join(
                subq,
                (IndicatorData.indicator_key == subq.c.indicator_key)
                & (IndicatorData.record_date == subq.c.latest_date),
            )
            .where(IndicatorData.member_id == member_id)
        )
        latest_indicators = latest_result.scalars().all()

        # Determine worst status
        status_priority = {"critical": 3, "high": 2, "low": 2, "normal": 1}
        worst_status = "normal"
        for ind in latest_indicators:
            if status_priority.get(ind.status, 0) > status_priority.get(worst_status, 0):
                worst_status = ind.status

        # Abnormal count in last 30 days
        thirty_days_ago = date.today() - timedelta(days=30)
        abnormal_result = await db.execute(
            select(func.count(IndicatorData.id))
            .where(
                IndicatorData.member_id == member_id,
                IndicatorData.record_date >= thirty_days_ago,
                IndicatorData.status != "normal",
            )
        )
        abnormal_count = abnormal_result.scalar() or 0

        return {
            "latest_status": worst_status,
            "abnormal_count": abnormal_count,
            "latest_indicators": [
                {
                    "indicator_key": ind.indicator_key,
                    "indicator_name": ind.indicator_name,
                    "value": float(ind.value) if ind.value is not None else None,
                    "unit": ind.unit,
                    "status": ind.status,
                    "record_date": ind.record_date.isoformat() if ind.record_date else None,
                }
                for ind in latest_indicators
            ],
        }

    @staticmethod
    async def get_family_dashboard(
        db: AsyncSession,
        family_id: str,
    ) -> list[dict]:
        """Return dashboard cards for all family members."""
        members = await MemberService.get_family_members(db, family_id)
        cards = []
        for member in members:
            dash = await MemberService.get_member_dashboard(db, member.id)
            cards.append(
                {
                    "id": member.id,
                    "name": member.name,
                    "avatar_url": member.avatar_url,
                    "type": member.type,
                    "role": member.role,
                    "birth_date": member.birth_date.isoformat() if member.birth_date else None,
                    **dash,
                }
            )
        return cards
