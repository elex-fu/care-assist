from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ocr_pipeline import run_ocr_pipeline


class TestOCRPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_normalizes_indicators(self):
        mock_items = [
            {"name": "收缩压", "value": 120, "unit": "mmHg", "raw_text": "收缩压 120"},
            {"name": "舒张压", "value": 80, "unit": "mmHg", "raw_text": "舒张压 80"},
        ]

        mock_provider = AsyncMock()
        mock_provider.extract_indicators = AsyncMock(return_value=mock_items)
        mock_provider.extract_text = AsyncMock(return_value="收缩压 120\n舒张压 80")
        mock_provider.name = MagicMock(return_value="baidu")

        with (
            patch("app.services.ocr_pipeline.get_ocr_provider", return_value=mock_provider),
            patch("app.services.ocr_pipeline.ocr_with_fallback", return_value=mock_items),
        ):
            result = await run_ocr_pipeline(["/tmp/report.png"])

        assert result.provider == "baidu"
        assert len(result.extracted) == 2
        keys = {item.indicator_key for item in result.extracted}
        assert "systolic_bp" in keys
        assert "diastolic_bp" in keys

    @pytest.mark.asyncio
    async def test_pipeline_skips_invalid_values(self):
        mock_items = [
            {"name": "收缩压", "value": 120, "unit": "mmHg"},
            {"name": "无效", "value": "abc", "unit": ""},
        ]

        mock_provider = AsyncMock()
        mock_provider.extract_indicators = AsyncMock(return_value=mock_items)
        mock_provider.extract_text = AsyncMock(return_value="")
        mock_provider.name = MagicMock(return_value="baidu")

        with (
            patch("app.services.ocr_pipeline.get_ocr_provider", return_value=mock_provider),
            patch("app.services.ocr_pipeline.ocr_with_fallback", return_value=mock_items),
        ):
            result = await run_ocr_pipeline(["/tmp/report.png"])

        assert len(result.extracted) == 1
        assert result.extracted[0].indicator_key == "systolic_bp"

    @pytest.mark.asyncio
    async def test_pipeline_deduplicates_by_key(self):
        mock_items = [
            {"name": "收缩压", "value": 120, "unit": "mmHg"},
            {"name": "收缩压", "value": 125, "unit": "mmHg"},
        ]

        mock_provider = AsyncMock()
        mock_provider.extract_indicators = AsyncMock(return_value=mock_items)
        mock_provider.extract_text = AsyncMock(return_value="")
        mock_provider.name = MagicMock(return_value="baidu")

        with (
            patch("app.services.ocr_pipeline.get_ocr_provider", return_value=mock_provider),
            patch("app.services.ocr_pipeline.ocr_with_fallback", return_value=mock_items),
        ):
            result = await run_ocr_pipeline(["/tmp/report.png"])

        assert len(result.extracted) == 1
