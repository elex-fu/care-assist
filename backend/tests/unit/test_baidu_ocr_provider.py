from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.baidu_ocr_provider import BaiduOCRProvider


class TestBaiduOCRProvider:
    @pytest.fixture
    def provider(self):
        p = BaiduOCRProvider()
        p.api_key = "test-key"
        p.secret_key = "test-secret"
        return p

    @pytest.mark.asyncio
    async def test_extract_text(self, provider, tmp_path):
        image_path = tmp_path / "report.png"
        image_path.write_bytes(b"fake-image-data")

        token_resp = MagicMock()
        token_resp.json.return_value = {"access_token": "fake-token"}
        token_resp.raise_for_status = MagicMock()

        ocr_resp = MagicMock()
        ocr_resp.json.return_value = {
            "words_result": [
                {"words": "收缩压 120 mmHg"},
                {"words": "舒张压 80 mmHg"},
            ]
        }
        ocr_resp.raise_for_status = MagicMock()

        client_instance = MagicMock()
        client_instance.post = AsyncMock(side_effect=[token_resp, ocr_resp])
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=client_instance):
            text = await provider.extract_text(str(image_path))

        assert "收缩压" in text
        assert "120" in text

    @pytest.mark.asyncio
    async def test_parse_indicators(self, provider):
        text = "收缩压 120 mmHg\n舒张压 80 mmHg\n空腹血糖 5.5 mmol/L"
        indicators = provider._parse_indicators(text)
        keys = {i["key"] for i in indicators}
        assert "systolic_bp" in keys
        assert "diastolic_bp" in keys
        assert "fasting_glucose" in keys

    def test_extract_value(self, provider):
        assert provider._extract_value("数值 12.5") == 12.5
        assert provider._extract_value("数值 100") == 100.0
        assert provider._extract_value("无数字") is None
