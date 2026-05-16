import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.services.export_service import export_excel, export_pdf, STATUS_COLORS


class TestExportExcel:
    async def test_export_excel_returns_bytesio(self):
        member = MagicMock()
        member.id = "test-id"
        member.name = "测试成员"
        member.type = "adult"
        member.gender = "male"
        member.blood_type = "A"
        member.birth_date = date(1990, 1, 1)

        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))

        result = await export_excel(db, member)
        assert hasattr(result, "read")
        result.seek(0)
        content = result.read()
        assert len(content) > 0
        assert content[:4] == b"PK\x03\x04"  # Excel (zip) magic number

    async def test_export_excel_with_indicators(self):
        member = MagicMock()
        member.id = "test-id"
        member.name = "测试成员"
        member.type = "adult"
        member.gender = "male"
        member.blood_type = None
        member.birth_date = None

        ind = MagicMock()
        ind.indicator_name = "收缩压"
        ind.value = Decimal("120")
        ind.unit = "mmHg"
        ind.status = "normal"
        ind.record_date = date(2024, 6, 15)

        empty_result = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
        ind_result = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[ind]))))

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[ind_result, empty_result, empty_result, empty_result, empty_result])

        result = await export_excel(db, member, start_date=date(2024, 1, 1), end_date=date(2024, 12, 31))
        assert hasattr(result, "read")
        result.seek(0)
        assert len(result.read()) > 0


class TestExportPDF:
    async def test_export_pdf_returns_bytesio(self):
        member = MagicMock()
        member.id = "test-id"
        member.name = "Test Member"
        member.type = "adult"
        member.gender = "male"
        member.blood_type = "O"
        member.birth_date = date(1990, 1, 1)

        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))

        result = await export_pdf(db, member)
        assert hasattr(result, "read")
        result.seek(0)
        content = result.read()
        assert len(content) > 0
        assert content[:4] == b"%PDF"  # PDF magic number


class TestStatusColors:
    def test_status_colors_defined(self):
        assert "normal" in STATUS_COLORS
        assert "critical" in STATUS_COLORS
        assert "pending" in STATUS_COLORS
        assert "completed" in STATUS_COLORS
