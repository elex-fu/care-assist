from app.core.indicator_engine import IndicatorEngine
from app.schemas.indicator_metadata import IndicatorMetadata


def _build_metadata() -> dict[str, IndicatorMetadata]:
    aliases_by_key: dict[str, list[str]] = {}
    for alias, key in IndicatorEngine.NAME_MAPPING.items():
        aliases_by_key.setdefault(key, []).append(alias)

    metadata: dict[str, IndicatorMetadata] = {}
    for key, config in IndicatorEngine.THRESHOLDS.items():
        threshold = config.get("threshold", {})
        lower = threshold.get("lower")
        upper = threshold.get("upper")
        unit = config.get("unit", "")
        ref_range = None
        if lower is not None and upper is not None:
            ref_range = f"{lower}-{upper} {unit}".strip()
        elif upper is not None:
            ref_range = f"≤{upper} {unit}".strip()
        elif lower is not None:
            ref_range = f"≥{lower} {unit}".strip()

        metadata[key] = IndicatorMetadata(
            key=key,
            name=config.get("name", key),
            aliases=aliases_by_key.get(key, []),
            unit=unit,
            ref_range=ref_range,
        )
    return metadata


_METADATA = _build_metadata()


def search_indicators(query: str, limit: int = 10) -> list[IndicatorMetadata]:
    """Fuzzy search indicator metadata by key, name, or alias."""
    q = query.strip().lower()
    if not q:
        return list(_METADATA.values())[:limit]

    results: list[IndicatorMetadata] = []
    seen: set[str] = set()
    for key, meta in _METADATA.items():
        if key in seen:
            continue
        if (
            q in key.lower()
            or q in meta.name.lower()
            or any(q in alias.lower() for alias in meta.aliases)
        ):
            results.append(meta)
            seen.add(key)
        if len(results) >= limit:
            break
    return results


def get_indicator_metadata(key: str) -> IndicatorMetadata | None:
    return _METADATA.get(key)
