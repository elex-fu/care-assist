import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.services.member_service import MemberService
from app.models.member import Member
from app.models.indicator import IndicatorData


class TestMemberService:
    async def test_get_family_members(self, db, test_family, test_creator, test_member):
        members = await MemberService.get_family_members(db, test_family.id)
        member_ids = [m.id for m in members]
        assert test_creator.id in member_ids
        assert test_member.id in member_ids

    async def test_get_member_dashboard_no_indicators(self, db, test_member):
        dash = await MemberService.get_member_dashboard(db, test_member.id)
        assert dash["latest_status"] == "normal"
        assert dash["abnormal_count"] == 0
        assert dash["latest_indicators"] == []

    async def test_get_member_dashboard_with_indicators(self, db, test_member):
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=Decimal("128"),
            unit="mmHg",
            status="high",
            deviation_percent=Decimal("5.0"),
            record_date=date.today(),
        ))
        await db.commit()

        dash = await MemberService.get_member_dashboard(db, test_member.id)
        assert dash["latest_status"] == "high"
        assert len(dash["latest_indicators"]) == 1
        assert dash["latest_indicators"][0]["indicator_key"] == "systolic_bp"

    async def test_get_member_dashboard_worst_status_critical(self, db, test_member):
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=Decimal("180"),
            unit="mmHg",
            status="critical",
            record_date=date.today(),
        ))
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="diastolic_bp",
            indicator_name="舒张压",
            value=Decimal("80"),
            unit="mmHg",
            status="normal",
            record_date=date.today(),
        ))
        await db.commit()

        dash = await MemberService.get_member_dashboard(db, test_member.id)
        assert dash["latest_status"] == "critical"

    async def test_get_member_dashboard_abnormal_count(self, db, test_member):
        today = date.today()
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=Decimal("140"),
            unit="mmHg",
            status="high",
            record_date=today,
        ))
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="glucose",
            indicator_name="血糖",
            value=Decimal("7.0"),
            unit="mmol/L",
            status="high",
            record_date=today - timedelta(days=5),
        ))
        # Old abnormal should not count
        db.add(IndicatorData(
            member_id=test_member.id,
            indicator_key="old",
            indicator_name="旧指标",
            value=Decimal("100"),
            unit="x",
            status="high",
            record_date=today - timedelta(days=31),
        ))
        await db.commit()

        dash = await MemberService.get_member_dashboard(db, test_member.id)
        # Count is of *records*, not distinct indicator keys
        assert dash["abnormal_count"] == 2

    async def test_get_family_dashboard(self, db, test_family, test_creator, test_member):
        db.add(IndicatorData(
            member_id=test_creator.id,
            indicator_key="systolic_bp",
            indicator_name="收缩压",
            value=Decimal("120"),
            unit="mmHg",
            status="normal",
            record_date=date.today(),
        ))
        await db.commit()

        cards = await MemberService.get_family_dashboard(db, test_family.id)
        assert len(cards) == 2
        creator_card = [c for c in cards if c["id"] == test_creator.id][0]
        assert creator_card["name"] == test_creator.name
        assert creator_card["latest_status"] == "normal"
