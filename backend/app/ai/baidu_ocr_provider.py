"""Baidu Cloud OCR provider."""

import base64
import os
import re
from typing import Any

import httpx

from app.ai.ocr_provider import OCRProvider
from app.config import settings
from app.core.indicator_search import search_indicators
from app.core.logging import get_logger

logger = get_logger("app.ai.baidu_ocr_provider")

_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
_OCR_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"


class BaiduOCRProvider(OCRProvider):
    """Baidu Cloud OCR provider.

    Requires BAIDU_OCR_API_KEY and BAIDU_OCR_SECRET_KEY in settings.
    """

    def __init__(self) -> None:
        self.api_key = settings.BAIDU_OCR_API_KEY
        self.secret_key = settings.BAIDU_OCR_SECRET_KEY
        self._access_token: str | None = None

    def name(self) -> str:
        return "baidu"

    async def _get_access_token(self) -> str:
        if self._access_token:
            return self._access_token
        if not self.api_key or not self.secret_key:
            raise RuntimeError("Baidu OCR API key/secret not configured")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _TOKEN_URL,
                params={
                    "grant_type": "client_credentials",
                    "client_id": self.api_key,
                    "client_secret": self.secret_key,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data.get("access_token")
            if not self._access_token:
                raise RuntimeError(f"Failed to get Baidu access token: {data}")
            return self._access_token

    def _read_image(self, image_url: str) -> bytes:
        if image_url.startswith("http://") or image_url.startswith("https://"):
            raise NotImplementedError("Remote image URLs are not supported yet")
        if not os.path.isabs(image_url):
            image_url = os.path.join(os.getcwd(), image_url)
        with open(image_url, "rb") as f:
            return f.read()

    async def extract_text(self, image_url: str) -> str:
        token = await self._get_access_token()
        image_bytes = self._read_image(image_url)
        encoded = base64.b64encode(image_bytes).decode("utf-8")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _OCR_URL,
                params={"access_token": token},
                data={"image": encoded},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()

        words = [item.get("words", "") for item in data.get("words_result", [])]
        return "\n".join(words)

    async def extract_indicators(self, image_url: str) -> list[dict[str, Any]]:
        text = await self.extract_text(image_url)
        return self._parse_indicators(text)

    def _parse_indicators(self, text: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        seen: set[str] = set()

        lines = text.splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Try to find a known indicator name anywhere in the line
            matched = self._match_indicator(line)
            if not matched:
                continue

            key, name, unit = matched
            if key in seen:
                continue

            value = self._extract_value(line)
            if value is None:
                continue

            results.append({
                "key": key,
                "name": name,
                "value": value,
                "unit": unit,
            })
            seen.add(key)

        return results

    def _match_indicator(self, line: str) -> tuple[str, str, str] | None:
        # Direct substring search for known names/aliases
        for meta in search_indicators("", limit=100):
            candidates = [meta.name] + meta.aliases
            for candidate in candidates:
                if candidate and candidate in line:
                    return meta.key, meta.name, meta.unit
        return None

    def _extract_value(self, line: str) -> float | None:
        # Look for numeric value, optionally with decimal
        match = re.search(r"(\d+(?:\.\d+)?)", line)
        if not match:
            return None
        try:
            return float(match.group(1))
        except ValueError:
            return None

    def __getstate__(self) -> dict[str, Any]:
        # Avoid pickling issues with httpx client
        state = self.__dict__.copy()
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)
