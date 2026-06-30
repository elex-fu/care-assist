from datetime import date, timedelta
from typing import TypedDict

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.indicator_search import get_indicator_metadata
from app.core.logging import get_logger
from app.models.indicator import IndicatorData
from app.models.member import Member
from app.schemas.chronic import (
    ChronicIndicatorItem,
    ChronicPackageListItem,
    ChronicPackageResponse,
    ChronicTrendOut,
    ChronicTrendPoint,
    ChronicTrendSeries,
)

logger = get_logger("app.core.chronic_packages")


class _ChronicPackageConfig(TypedDict):
    name: str
    description: str
    indicator_keys: list[str]


CHRONIC_PACKAGES: dict[str, _ChronicPackageConfig] = {
    "hypertension": {
        "name": "高血压",
        "description": "监测收缩压、舒张压等血压相关指标",
        "indicator_keys": ["systolic_bp", "diastolic_bp"],
    },
    "diabetes": {
        "name": "糖尿病",
        "description": "监测空腹血糖、糖化血红蛋白等血糖相关指标",
        "indicator_keys": ["fasting_glucose", "hba1c"],
    },
    "dyslipidemia": {
        "name": "高血脂",
        "description": "监测总胆固醇、低密度脂蛋白等血脂相关指标",
        "indicator_keys": ["total_cholesterol", "ldl"],
    },
}


def list_chronic_packages() -> list[ChronicPackageListItem]:
    return [
        ChronicPackageListItem(package=key, name=config["name"], description=config["description"])
        for key, config in CHRONIC_PACKAGES.items()
    ]


async def build_chronic_package(
    package: str,
    member: Member,
    db: AsyncSession,
) -> ChronicPackageResponse:
    config = CHRONIC_PACKAGES.get(package)
    if not config:
        raise ValueError(f"Unknown chronic package: {package}")

    keys = config["indicator_keys"]
    end_date = date.today()
    start_date = end_date - timedelta(days=90)

    result = await db.execute(
        select(IndicatorData)
        .where(
            IndicatorData.member_id == member.id,
            IndicatorData.indicator_key.in_(keys),
            IndicatorData.record_date >= start_date,
            IndicatorData.record_date <= end_date,
        )
        .order_by(desc(IndicatorData.record_date), desc(IndicatorData.created_at))
    )
    records = result.scalars().all()

    # Keep latest record per indicator key
    latest_by_key: dict[str, IndicatorData] = {}
    for r in records:
        if r.indicator_key not in latest_by_key:
            latest_by_key[r.indicator_key] = r

    indicators: list[ChronicIndicatorItem] = []
    for key in keys:
        meta = get_indicator_metadata(key)
        record = latest_by_key.get(key)
        if record:
            indicators.append(ChronicIndicatorItem(
                key=key,
                name=meta.name if meta else key,
                value=float(record.value) if record.value is not None else None,
                unit=record.unit or (meta.unit if meta else ""),
                status=record.status or "unknown",
                ref_range=meta.ref_range if meta else None,
            ))
        else:
            indicators.append(ChronicIndicatorItem(
                key=key,
                name=meta.name if meta else key,
                value=None,
                unit=meta.unit if meta else "",
                status="no_data",
                ref_range=meta.ref_range if meta else None,
            ))

    summary = await generate_chronic_summary(package, indicators)

    return ChronicPackageResponse(
        package=package,
        name=config["name"],
        indicators=indicators,
        summary=summary,
    )


async def build_chronic_trend(
    package: str,
    member: Member,
    db: AsyncSession,
    days: int = 180,
) -> ChronicTrendOut:
    """Build a multi-indicator trend for a chronic disease package."""
    config = CHRONIC_PACKAGES.get(package)
    if not config:
        raise ValueError(f"Unknown chronic package: {package}")

    keys = config["indicator_keys"]
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    result = await db.execute(
        select(IndicatorData)
        .where(
            IndicatorData.member_id == member.id,
            IndicatorData.indicator_key.in_(keys),
            IndicatorData.record_date >= start_date,
            IndicatorData.record_date <= end_date,
        )
        .order_by(IndicatorData.record_date, IndicatorData.created_at)
    )
    records = result.scalars().all()

    # Group records by indicator key while preserving chronological order.
    points_by_key: dict[str, list[ChronicTrendPoint]] = {key: [] for key in keys}
    for r in records:
        if r.indicator_key not in points_by_key:
            continue
        points_by_key[r.indicator_key].append(ChronicTrendPoint(
            value=float(r.value) if r.value is not None else 0.0,
            record_date=r.record_date,
            status=r.status or "unknown",
        ))

    series: list[ChronicTrendSeries] = []
    for key in keys:
        meta = get_indicator_metadata(key)
        points = points_by_key[key]
        trend_direction = _calculate_trend_direction(points)
        series.append(ChronicTrendSeries(
            indicator_key=key,
            indicator_name=meta.name if meta else key,
            unit=meta.unit if meta else "",
            points=points,
            trend_direction=trend_direction,
        ))

    return ChronicTrendOut(
        package=package,
        member_id=member.id,
        series=series,
    )


def _calculate_trend_direction(points: list[ChronicTrendPoint]) -> str:
    if len(points) < 2:
        return "stable"
    first = points[0].value
    last = points[-1].value
    if first == 0:
        return "stable"
    change = (last - first) / abs(first)
    if change > 0.05:
        return "up"
    if change < -0.05:
        return "down"
    return "stable"


async def generate_chronic_summary(package: str, indicators: list[ChronicIndicatorItem]) -> str:
    # Rule-based fallback always available
    rule_summary = _generate_rule_summary(package, indicators)

    # Try AI only if a provider is configured
    try:
        from app.ai.factory import chat_with_fallback
        from app.config import settings

        if not settings.DEFAULT_AI_PROVIDER:
            return rule_summary

        prompt = _build_ai_prompt(package, indicators)
        ai_summary = await chat_with_fallback(
            [
                {"role": "system", "content": "你是一名健康助理，请根据用户的指标数据生成一段简短（不超过80字）的中文病情监测总结，语气平和、建议就医时明确说明。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=256,
            temperature=0.5,
        )
        return (ai_summary or rule_summary).strip() or rule_summary
    except Exception as exc:
        logger.warning(f"AI chronic summary failed for {package}: {exc}")
        return rule_summary


def _generate_rule_summary(package: str, indicators: list[ChronicIndicatorItem]) -> str:
    abnormal = [i for i in indicators if i.status in ("low", "high", "critical")]
    critical = [i for i in indicators if i.status == "critical"]
    no_data = [i for i in indicators if i.status == "no_data"]

    if critical:
        names = "、".join(i.name for i in critical)
        return f"{names}处于危急范围，建议尽快就医复查。"
    if abnormal:
        names = "、".join(i.name for i in abnormal)
        return f"{names}偏离参考范围，建议关注并咨询医生。"
    if no_data and len(no_data) == len(indicators):
        return "近90天内未记录相关指标，建议定期检测。"
    if no_data:
        names = "、".join(i.name for i in no_data)
        return f"部分指标（{names}）近90天无记录，其余指标目前正常。"
    return "当前指标均在参考范围内，情况正常，请继续保持并定期监测。"


def _build_ai_prompt(package: str, indicators: list[ChronicIndicatorItem]) -> str:
    lines = [f"慢性病套餐：{CHRONIC_PACKAGES[package]['name']}", "指标数据："]
    for i in indicators:
        value_text = f"{i.value} {i.unit}" if i.value is not None else "无数据"
        lines.append(f"- {i.name}: {value_text}，状态：{i.status}")
    return "\n".join(lines)
