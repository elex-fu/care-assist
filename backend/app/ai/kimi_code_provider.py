"""Kimi Code provider using OpenAI-compatible chat completions.

Kimi Code endpoint: https://api.kimi.com/coding/v1/chat/completions
"""

from __future__ import annotations

import base64
import json
import os
from collections.abc import AsyncIterator

import httpx

from app.ai.provider import AIProvider
from app.config import settings
from app.core.exceptions import BusinessException


class KimiCodeProvider(AIProvider):
    """Kimi Code provider using OpenAI-compatible chat completions."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or settings.KIMI_CODE_API_KEY
        self.base_url = (base_url or settings.KIMI_CODE_BASE_URL).rstrip("/")
        self.model = model or settings.KIMI_CODE_MODEL
        self.timeout = settings.KIMI_CODE_TIMEOUT

        if not self.api_key:
            raise BusinessException("KIMI_CODE_API_KEY is not configured")

    def name(self) -> str:
        return "kimi-code"

    async def chat(
        self,
        messages: list[dict],
        *,
        stream: bool = False,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AsyncIterator[str] | str:
        """Call Kimi Code /v1/chat/completions endpoint (OpenAI protocol)."""
        # kimi-for-coding only allows temperature=1.0.
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 1.0,
            "stream": stream,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "KimiCLI/1.6",
        }

        url = f"{self.base_url}/chat/completions"

        if stream:
            return self._stream_chat(url, headers, payload)
        return await self._non_stream_chat(url, headers, payload)

    async def _non_stream_chat(
        self,
        url: str,
        headers: dict,
        payload: dict,
    ) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            self._raise_for_status(response)
            data = response.json()
        message = data.get("choices", [{}])[0].get("message", {})
        # Some kimi-for-coding responses include reasoning_content before content.
        return message.get("content", "")

    async def _stream_chat(
        self,
        url: str,
        headers: dict,
        payload: dict,
    ) -> AsyncIterator[str]:
        headers["Accept"] = "text/event-stream"
        async with (
            httpx.AsyncClient(timeout=self.timeout) as client,
            client.stream("POST", url, headers=headers, json=payload) as response,
        ):
            self._raise_for_status(response)
            async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    text = delta.get("content", "")
                    if text:
                        yield text

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            try:
                body = response.json()
                message = body.get("error", {}).get("message") or body.get("error") or str(body)
            except Exception:
                message = response.text or f"HTTP {response.status_code}"
            raise BusinessException(f"Kimi Code API error ({response.status_code}): {message}")

    async def analyze_image(self, image_url: str, prompt: str) -> str:
        """Analyze an image using vision-capable model."""
        content = [{"type": "text", "text": prompt}]
        if image_url.startswith("http://") or image_url.startswith("https://"):
            content.append({"type": "image_url", "image_url": {"url": image_url}})
        else:
            # Local file path: read and base64 encode.
            path = image_url if os.path.isabs(image_url) else os.path.join(os.getcwd(), image_url)
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            ext = os.path.splitext(path)[1].lower()
            media_type = "image/png" if ext == ".png" else "image/jpeg"
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}}
            )

        messages = [
            {"role": "system", "content": "You are a medical report analysis assistant."},
            {"role": "user", "content": content},
        ]
        return await self.chat(messages, stream=False, max_tokens=2048)

    async def generate_summary(self, context: dict) -> str:
        """Generate a family health summary from context."""
        prompt = self._build_summary_prompt(context)
        messages = [
            {"role": "system", "content": "You are a family health assistant."},
            {"role": "user", "content": prompt},
        ]
        return await self.chat(messages, stream=False, max_tokens=1024)

    def _build_summary_prompt(self, context: dict) -> str:
        member_cards = context.get("member_cards", [])
        lines = ["请根据以下家庭成员健康数据生成一段简短的中文健康日报："]
        for card in member_cards:
            lines.append(
                f"- {card.get('name', '成员')}（{card.get('type', '成人')}）: "
                f"最新状态 {card.get('latest_status', '正常')}, "
                f"异常指标数 {card.get('abnormal_count', 0)}"
            )
        lines.append(
            "要求：1. 用温暖的中文；2. 异常成员优先提醒；"
            "3. 给出具体可操作建议；4. 不超过150字。"
        )
        return "\n".join(lines)
