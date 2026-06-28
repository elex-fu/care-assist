"""Kimi Code OCR provider using OpenAI-compatible chat completions.

The Kimi Code coding endpoint supports standard `/chat/completions`:
    https://api.kimi.com/coding/v1/chat/completions

Default model: "kimi-for-coding"
Authentication: Authorization: Bearer <KIMI_CODE_API_KEY>

This provider sends a base64-encoded image to the model and asks for
structured indicator JSON. If the configured model does not support vision,
the API will return a 400-level error and the demo/test will surface that.
"""

from __future__ import annotations

import base64
import json
import os
import re
from typing import Any

import httpx

from app.ai.ocr_provider import OCRProvider
from app.config import settings
from app.core.indicator_search import search_indicators
from app.core.logging import get_logger

logger = get_logger("app.ai.kimi_ocr_provider")

_KIMI_CODE_BASE_URL = "https://api.kimi.com/coding/v1"


class KimiOCRProvider(OCRProvider):
    """OCR provider backed by a Kimi Code / Moonshot vision model."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        # Primary: Kimi Code endpoint; secondary: Moonshot public API.
        self.api_key = api_key or settings.KIMI_CODE_API_KEY or settings.MOONSHOT_API_KEY
        self.base_url = (
            base_url
            or settings.KIMI_CODE_BASE_URL
            or _KIMI_CODE_BASE_URL
        ).rstrip("/")
        self.model = (
            model
            or settings.KIMI_CODE_OCR_MODEL
            or settings.MOONSHOT_OCR_MODEL
            or "kimi-for-coding"
        )
        self.timeout = settings.KIMI_CODE_TIMEOUT

        if not self.api_key:
            raise RuntimeError(
                "Kimi OCR requires KIMI_CODE_API_KEY or MOONSHOT_API_KEY"
            )

    def name(self) -> str:
        return "kimi"

    def _read_image(self, image_url: str) -> bytes:
        if image_url.startswith("http://") or image_url.startswith("https://"):
            raise NotImplementedError(
                "Remote image URLs are not supported yet; please pass a local path"
            )
        if not os.path.isabs(image_url):
            image_url = os.path.join(os.getcwd(), image_url)
        with open(image_url, "rb") as f:
            return f.read()

    async def extract_text(self, image_url: str) -> str:
        """Extract raw text from the image using Kimi vision."""
        image_bytes = self._read_image(image_url)
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        media_type = self._guess_media_type(image_url)

        prompt = (
            "请识别这张医疗/体检报告图片中的所有文字，保持原始排版，"
            "直接返回识别到的文本，不要解释。"
        )
        response = await self._call_vision_model(b64, media_type, prompt)
        return response

    async def extract_indicators(self, image_url: str) -> list[dict[str, Any]]:
        """Extract structured health indicators from the image."""
        image_bytes = self._read_image(image_url)
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        media_type = self._guess_media_type(image_url)

        known_indicators = self._build_indicator_catalog_prompt()
        prompt = (
            "你是一位医学检验单识别助手。请仔细查看图片，提取所有可识别的"
            "健康指标（如血压、血糖、血脂、身高、体重、血常规项目等）。\n\n"
            "已知指标参考：\n" + known_indicators + "\n\n"
            "请以 JSON 格式返回，不要添加任何额外说明。JSON 结构如下：\n"
            '{"indicators": [{"name": "指标中文名", "value": 数值或字符串, '
            '"unit": "单位", "raw_text": "图片中原始行文本"}]}\n\n'
            "如果某个值是范围（如 3.5-5.0），取中间值；如果无法识别单位，"
            "根据常见医学指标推断。若图片中没有任何指标，返回空数组。"
        )
        response = await self._call_vision_model(b64, media_type, prompt)
        return self._parse_indicators(response)

    async def _call_vision_model(
        self, b64_image: str, media_type: str, prompt: str
    ) -> str:
        """Call the vision model with a base64-encoded image."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "KimiCLI/1.6",
        }

        messages = [
            {
                "role": "system",
                "content": (
                    "你是医学报告识别助手。请只按用户要求的格式输出，"
                    "不要添加解释或 Markdown 代码块标记。"
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{b64_image}"
                        },
                    },
                ],
            },
        ]

        # kimi-for-coding only allows temperature=1.0.
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 1.0,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        logger.info(f"Kimi OCR response preview: {content[:200]}...")
        if not content:
            logger.warning(f"Kimi OCR returned empty content. Full response: {data}")
        return content

    def _guess_media_type(self, path: str) -> str:
        ext = os.path.splitext(path)[1].lower()
        mapping = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        return mapping.get(ext, "image/jpeg")

    def _build_indicator_catalog_prompt(self) -> str:
        """Build a compact catalog of known indicators for the prompt."""
        lines = []
        for meta in search_indicators("", limit=200):
            alias_hint = meta.aliases[0] if meta.aliases else meta.name
            lines.append(f"- {meta.name}({alias_hint}) 单位:{meta.unit}")
        return "\n".join(lines[:100])  # Limit prompt size

    def _parse_indicators(self, response: str) -> list[dict[str, Any]]:
        """Parse model response JSON and normalize to indicator dicts."""
        results: list[dict[str, Any]] = []
        seen: set[str] = set()

        # Try to extract a JSON object from the response.
        text = response.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"Kimi OCR returned non-JSON response: {response[:200]}")
            return results

        indicators = parsed.get("indicators", []) if isinstance(parsed, dict) else []
        if not isinstance(indicators, list):
            return results

        for item in indicators:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue

            matched = self._match_indicator(name)
            if not matched:
                continue

            key, canonical_name, unit = matched
            if key in seen:
                continue

            value = self._extract_value(str(item.get("value", "")))
            if value is None:
                continue

            results.append({
                "key": key,
                "name": canonical_name,
                "value": value,
                "unit": unit,
                "raw_text": item.get("raw_text", name),
            })
            seen.add(key)

        return results

    def _match_indicator(self, text: str) -> tuple[str, str, str] | None:
        """Match extracted name to a known indicator key."""
        text = text.lower()
        for meta in search_indicators("", limit=200):
            candidates = [meta.name] + meta.aliases
            for candidate in candidates:
                if candidate and candidate.lower() in text:
                    return meta.key, meta.name, meta.unit
        return None

    def _extract_value(self, value_text: str) -> float | None:
        """Extract a numeric value from text, handling ranges by taking midpoint."""
        value_text = str(value_text).strip()
        if not value_text:
            return None

        # Range like "3.5-5.0" or "3.5~5.0"
        range_match = re.search(r"(\d+(?:\.\d+)?)\s*[-~]\s*(\d+(?:\.\d+)?)", value_text)
        if range_match:
            low = float(range_match.group(1))
            high = float(range_match.group(2))
            return round((low + high) / 2, 2)

        number_match = re.search(r"(\d+(?:\.\d+)?)", value_text)
        if number_match:
            try:
                return float(number_match.group(1))
            except ValueError:
                return None
        return None
