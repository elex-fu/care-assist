"""Annual health summary aggregation service."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.member import Member
from app.models.indicator import IndicatorData
from app.models.report import Report
from app.models.health_event import HealthEvent
from app.models.hospital import HospitalEvent


class SummaryService:
    @staticmethod
    async def get_annual_summary(db: AsyncSession, family_id: str, year: int | None = None) -> dict:
        """Aggregate annual health summary for a family."""
        if year is None:
            year = date.today().year

        start = date(year, 1, 1)
        end = date(year, 12, 31)

        members_result = await db.execute(select(Member).where(Member.family_id == family_id))
        members = members_result.scalars().all()
        member_ids = [m.id for m in members]

        # Family totals
        indicator_count = await db.scalar(
            select(func.count(IndicatorData.id))
            .where(
                IndicatorData.member_id.in_(member_ids),
                IndicatorData.record_date >= start,
                IndicatorData.record_date <= end,
            )
        ) or 0

        report_count = await db.scalar(
            select(func.count(Report.id))
            .where(
                Report.member_id.in_(member_ids),
                Report.report_date >= start,
                Report.report_date <= end,
            )
        ) or 0

        event_count = await db.scalar(
            select(func.count(HealthEvent.id))
            .where(
                HealthEvent.member_id.in_(member_ids),
                HealthEvent.event_date >= start,
                HealthEvent.event_date <= end,
            )
        ) or 0

        hospital_count = await db.scalar(
            select(func.count(HospitalEvent.id))
            .where(
                HospitalEvent.member_id.in_(member_ids),
                HospitalEvent.admission_date >= start,
                HospitalEvent.admission_date <= end,
            )
        ) or 0

        abnormal_count = await db.scalar(
            select(func.count(IndicatorData.id))
            .where(
                IndicatorData.member_id.in_(member_ids),
                IndicatorData.record_date >= start,
                IndicatorData.record_date <= end,
                IndicatorData.status != "normal",
            )
        ) or 0

        # Per-member stats
        member_stats = []
        for m in members:
            ind_count = await db.scalar(
                select(func.count(IndicatorData.id))
                .where(
                    IndicatorData.member_id == m.id,
                    IndicatorData.record_date >= start,
                    IndicatorData.record_date <= end,
                )
            ) or 0

            rep_count = await db.scalar(
                select(func.count(Report.id))
                .where(
                    Report.member_id == m.id,
                    Report.report_date >= start,
                    Report.report_date <= end,
                )
            ) or 0

            abn_count = await db.scalar(
                select(func.count(IndicatorData.id))
                .where(
                    IndicatorData.member_id == m.id,
                    IndicatorData.record_date >= start,
                    IndicatorData.record_date <= end,
                    IndicatorData.status != "normal",
                )
            ) or 0

            member_stats.append({
                "id": m.id,
                "name": m.name,
                "type": m.type,
                "indicator_count": ind_count,
                "report_count": rep_count,
                "abnormal_count": abn_count,
            })

        # Simple achievements
        achievements = []
        if indicator_count >= 50:
            achievements.append({"icon": "📊", "title": "数据达人", "desc": f"全年记录 {indicator_count} 项指标"})
        if report_count >= 10:
            achievements.append({"icon": "📄", "title": "报告收藏家", "desc": f"全年上传 {report_count} 份报告"})
        if event_count >= 20:
            achievements.append({"icon": "📅", "title": "健康管家", "desc": f"全年记录 {event_count} 个健康事件"})
        if hospital_count == 0:
            achievements.append({"icon": "💪", "title": "平安健康", "desc": "全年无住院记录"})
        if abnormal_count == 0 and indicator_count > 0:
            achievements.append({"icon": "🌟", "title": "指标全优", "desc": "全年指标全部正常"})

        return {
            "year": year,
            "family_id": family_id,
            "total_members": len(members),
            "indicator_count": indicator_count,
            "report_count": report_count,
            "event_count": event_count,
            "hospital_count": hospital_count,
            "abnormal_count": abnormal_count,
            "members": member_stats,
            "achievements": achievements,
        }
