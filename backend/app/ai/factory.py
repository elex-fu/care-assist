"""AI Provider factory with fallback support."""

import logging
from typing import Optional

from app.ai.provider import AIProvider
from app.ai.kimi_code_provider import KimiCodeProvider
from app.config import settings

logger = logging.getLogger(__name__)

_PROVIDER_REGISTRY: dict[str, type[AIProvider]] = {
    "kimi-code": KimiCodeProvider,
}


def list_providers() -> list[str]:
    """Return available provider names."""
    return list(_PROVIDER_REGISTRY.keys())


def get_provider(name: Optional[str] = None) -> AIProvider:
    """Get a provider instance by name.

    Args:
        name: Provider name. Defaults to settings.DEFAULT_AI_PROVIDER.

    Raises:
        ValueError: If provider name is unknown.
    """
    name = (name or settings.DEFAULT_AI_PROVIDER or "kimi-code").lower()
    provider_cls = _PROVIDER_REGISTRY.get(name)
    if not provider_cls:
        raise ValueError(
            f"Unknown AI provider: {name}. "
            f"Available providers: {', '.join(list_providers())}"
        )
    return provider_cls()


def get_default_provider() -> AIProvider:
    """Return the default configured provider."""
    return get_provider()


async def chat_with_fallback(
    messages: list[dict],
    *,
    stream: bool = False,
    max_tokens: int = 1024,
    temperature: float = 0.7,
) -> str:
    """Chat with configured provider, falling back to fallback providers on failure.

    Returns:
        Complete response string.

    Raises:
        RuntimeError: If all providers fail.
    """
    providers = [settings.DEFAULT_AI_PROVIDER] + settings.FALLBACK_AI_PROVIDERS
    providers = [p for p in providers if p]

    last_error: Optional[Exception] = None
    for provider_name in providers:
        try:
            provider = get_provider(provider_name)
            return await provider.chat(
                messages,
                stream=stream,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as exc:
            logger.warning(f"AI provider {provider_name} failed: {exc}")
            last_error = exc
            continue

    raise RuntimeError(f"All AI providers failed. Last error: {last_error}")
