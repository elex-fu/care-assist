import os
import tempfile
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.kimi_ocr_provider import KimiOCRProvider


@pytest.fixture
def provider():
    return KimiOCRProvider(
        api_key="test-key",
        base_url="https://api.moonshot.cn/v1",
        model="kimi-latest",
    )


@pytest.fixture
def dummy_image_path():
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.write(fd, b"fake-jpg-data")
    os.close(fd)
    yield path
    os.remove(path)


@pytest.mark.asyncio
async def test_extract_indicators_parses_json_response(provider, dummy_image_path):
    fake_response = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"indicators": [{"name": "收缩压", "value": "145", '
                        '"unit": "mmHg", "raw_text": "收缩压 145 mmHg"}]}'
                    )
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json = lambda: fake_response
        result = await provider.extract_indicators(dummy_image_path)

    assert len(result) == 1
    assert result[0]["key"] == "systolic_bp"
    assert result[0]["name"] == "收缩压"
    assert result[0]["value"] == 145.0
    assert result[0]["unit"] == "mmHg"


@pytest.mark.asyncio
async def test_extract_indicators_handles_range_value(provider, dummy_image_path):
    fake_response = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"indicators": [{"name": "总胆固醇", "value": "3.5-5.0", '
                        '"unit": "mmol/L"}]}'
                    )
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json = lambda: fake_response
        result = await provider.extract_indicators(dummy_image_path)

    assert len(result) == 1
    assert result[0]["key"] == "total_cholesterol"
    assert result[0]["value"] == 4.25


def test_extract_value_parses_various_formats(provider):
    assert provider._extract_value("120") == 120.0
    assert provider._extract_value("5.2 mmol/L") == 5.2
    assert provider._extract_value("3.5-5.0") == 4.25
    assert provider._extract_value("<0.5") == 0.5


def test_guess_media_type(provider):
    assert provider._guess_media_type("report.png") == "image/png"
    assert provider._guess_media_type("report.jpg") == "image/jpeg"
    assert provider._guess_media_type("report.webp") == "image/webp"
