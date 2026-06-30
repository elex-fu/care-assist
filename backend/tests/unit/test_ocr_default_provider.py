from app.ai.factory import get_ocr_provider, list_ocr_providers
from app.ai.kimi_ocr_provider import KimiOCRProvider
from app.config import settings


def test_kimi_ocr_provider_is_registered():
    assert "kimi" in list_ocr_providers()


def test_default_ocr_provider_is_kimi():
    # Ensure the default is kimi when no explicit override is set.
    original = settings.OCR_PROVIDER
    try:
        settings.OCR_PROVIDER = ""
        provider = get_ocr_provider()
        assert isinstance(provider, KimiOCRProvider)
    finally:
        settings.OCR_PROVIDER = original
