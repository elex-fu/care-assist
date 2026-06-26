from typing import Any

from app.ai.factory import get_ocr_provider, ocr_with_fallback
from app.core.indicator_search import search_indicators
from app.core.logging import get_logger
from app.schemas.ocr import OCRPipelineResult, OCRResultItem

logger = get_logger("app.services.ocr_pipeline")


def _normalize_indicator(raw: dict[str, Any]) -> OCRResultItem | None:
    """Normalize a raw OCR indicator dict to a structured item."""
    name = raw.get("name") or raw.get("indicator_name", "")
    value = raw.get("value")
    unit = raw.get("unit", "")

    if value is None:
        return None
    try:
        value = float(value)
    except (ValueError, TypeError):
        return None

    # Try to match known indicator by name/alias
    matches = search_indicators(name, limit=1) if name else []
    if matches:
        meta = matches[0]
        return OCRResultItem(
            indicator_key=meta.key,
            indicator_name=meta.name,
            value=value,
            unit=unit or meta.unit,
            raw_text=raw.get("raw_text", ""),
        )

    # Fallback to raw key/name if provided
    key = raw.get("key") or raw.get("indicator_key") or name
    if not key:
        return None
    return OCRResultItem(
        indicator_key=key,
        indicator_name=name or key,
        value=value,
        unit=unit,
        raw_text=raw.get("raw_text", ""),
    )


async def run_ocr_pipeline(image_paths: list[str]) -> OCRPipelineResult:
    """Run OCR on a list of image paths and normalize extracted indicators.

    Args:
        image_paths: List of image file paths.

    Returns:
        OCRPipelineResult with extracted indicators and raw text.
    """
    provider = get_ocr_provider()
    all_extracted: list[OCRResultItem] = []
    all_raw_texts: list[str] = []
    seen_keys: set[str] = set()

    for path in image_paths:
        try:
            raw_items = await ocr_with_fallback(path)
            raw_text = await provider.extract_text(path)
            all_raw_texts.append(raw_text)

            for raw in raw_items:
                item = _normalize_indicator(raw)
                if not item:
                    continue
                if item.indicator_key in seen_keys:
                    continue
                seen_keys.add(item.indicator_key)
                all_extracted.append(item)
        except Exception as exc:
            logger.warning(f"OCR failed for {path}: {exc}")

    return OCRPipelineResult(
        extracted=all_extracted,
        raw_text="\n".join(all_raw_texts),
        provider=provider.name(),
    )
