"""OCR Provider abstract interface."""

from abc import ABC, abstractmethod


class OCRProvider(ABC):
    """Abstract interface for OCR providers."""

    @abstractmethod
    async def extract_text(self, image_url: str) -> str:
        """Extract raw text from an image.

        Args:
            image_url: Publicly accessible URL or local file path of the image.

        Returns:
            Extracted raw text.
        """
        pass

    @abstractmethod
    async def extract_indicators(self, image_url: str) -> list[dict]:
        """Extract health indicators from an image.

        Args:
            image_url: Publicly accessible URL or local file path of the image.

        Returns:
            List of indicator dicts, e.g. [{"name": "收缩压", "value": 120, "unit": "mmHg"}].
        """
        pass

    @abstractmethod
    def name(self) -> str:
        """Return provider name."""
        pass
