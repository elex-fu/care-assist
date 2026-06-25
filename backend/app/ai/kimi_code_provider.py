"""Kimi Code provider using Anthropic Messages API protocol.

Kimi Code endpoint: https://api.kimi.com/coding/v1/messages
Reference: model-router upstream configuration for kimi-code.
"""

import json
from typing import AsyncIterator, Union

import httpx

from app.ai.provider import AIProvider
from app.config import settings
from app.core.exceptions import BusinessException


class KimiCodeProvider(AIProvider):
    """Kimi Code provider.

    Uses Anthropic Messages API format through the Kimi Code coding endpoint.
    """

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
    ) -> Union[AsyncIterator[str], str]:
        """Call Kimi Code /v1/messages endpoint (Anthropic protocol)."""
        # Convert OpenAI-style messages to Anthropic format if needed.
        # Anthropic supports system as a top-level field, user/assistant in messages.
        system_message = None
        chat_messages = []
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "system":
                system_message = content
            elif role in ("user", "assistant"):
                chat_messages.append({"role": role, "content": content})

        payload: dict = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if system_message:
            payload["system"] = system_message
        if temperature is not None:
            payload["temperature"] = temperature

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "claude-code-20250219",
        }

        url = f"{self.base_url}/v1/messages"

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
            content_blocks = data.get("content", [])
            text_parts = [
                block.get("text", "")
                for block in content_blocks
                if block.get("type") == "text"
            ]
            return "".join(text_parts)

    async def _stream_chat(
        self,
        url: str,
        headers: dict,
        payload: dict,
    ) -> AsyncIterator[str]:
        headers["Accept"] = "text/event-stream"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                self._raise_for_status(response)
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    # Support both "data: {...}" and "data:{...}" formats
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    event_type = data.get("type")
                    if event_type == "content_block_delta":
                        delta = data.get("delta", {})
                        if delta.get("type") == "text_delta":
                            yield delta.get("text", "")
                    elif event_type == "message_delta":
                        # end of message
                        pass

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            try:
                body = response.json()
                message = body.get("error", {}).get("message") or body.get("error") or str(body)
            except Exception:
                message = response.text or f"HTTP {response.status_code}"
            raise BusinessException(f"Kimi Code API error ({response.status_code}): {message}")

    async def analyze_image(self, image_url: str, prompt: str) -> str:
        """Analyze image using vision-capable model.

        Note: Kimi Code may not support vision. This method falls back to
        describing the task via text if image analysis is unavailable.
        """
        messages = [
            {"role": "system", "content": "You are a medical report analysis assistant."},
            {
                "role": "user",
                "content": f"{prompt}\nImage URL: {image_url}",
            },
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
        lines.append("要求：1. 用温暖的中文；2. 异常成员优先提醒；3. 给出具体可操作建议；4. 不超过150字。")
        return "\n".join(lines)
