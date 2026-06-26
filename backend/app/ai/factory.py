"""AI Provider factory with fallback support."""

from typing import Optional

from app.ai.provider import AIProvider
from app.ai.kimi_code_provider import KimiCodeProvider
from app.ai.ocr_provider import OCRProvider
from app.ai.baidu_ocr_provider import BaiduOCRProvider
from app.ai.tencent_ocr_provider import TencentOCRProvider
from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_PROVIDER_REGISTRY: dict[str, type[AIProvider]] = {
    "kimi-code": KimiCodeProvider,
}

_OCR_PROVIDER_REGISTRY: dict[str, type[OCRProvider]] = {}


def list_providers() -> list[str]:
    """Return available AI provider names."""
    return list(_PROVIDER_REGISTRY.keys())


def get_provider(name: Optional[str] = None) -> AIProvider:
    """Get an AI provider instance by name.

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
    """Return the default configured AI provider."""
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


def register_ocr_provider(name: str, provider_cls: type[OCRProvider]) -> None:
    """Register an OCR provider class by name."""
    _OCR_PROVIDER_REGISTRY[name.lower()] = provider_cls


def list_ocr_providers() -> list[str]:
    """Return available OCR provider names."""
    return list(_OCR_PROVIDER_REGISTRY.keys())


def get_ocr_provider(name: Optional[str] = None) -> OCRProvider:
    """Get an OCR provider instance by name.

    Defaults to settings.OCR_PROVIDER.

    Raises:
        ValueError: If provider name is unknown.
    """
    name = (name or settings.OCR_PROVIDER or "mock").lower()
    provider_cls = _OCR_PROVIDER_REGISTRY.get(name)
    if not provider_cls:
        raise ValueError(
            f"Unknown OCR provider: {name}. "
            f"Available providers: {', '.join(list_ocr_providers())}"
        )
    return provider_cls()


async def ocr_with_fallback(image_url: str) -> list[dict]:
    """Run OCR with configured provider.

    Returns:
        List of extracted indicator dicts.
    """
    provider = get_ocr_provider()
    logger.info(f"OCR using provider: {provider.name()}")
    return await provider.extract_indicators(image_url)


register_ocr_provider("baidu", BaiduOCRProvider)
register_ocr_provider("tencent", TencentOCRProvider)
