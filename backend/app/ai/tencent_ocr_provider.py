"""Tencent Cloud OCR provider (placeholder)."""

from app.ai.ocr_provider import OCRProvider
from app.core.logging import get_logger

logger = get_logger("app.ai.tencent_ocr_provider")


class TencentOCRProvider(OCRProvider):
    """Tencent Cloud OCR provider — placeholder implementation.

    Real integration requires `tencentcloud-sdk-python` and configured
    TENCENT_OCR_SECRET_ID / TENCENT_OCR_SECRET_KEY.
    """

    def name(self) -> str:
        return "tencent"

    async def extract_text(self, image_url: str) -> str:
        logger.warning("Tencent OCR is a placeholder; returning empty text")
        return ""

    async def extract_indicators(self, image_url: str) -> list[dict]:
        logger.warning("Tencent OCR is a placeholder; returning empty indicators")
        return []
