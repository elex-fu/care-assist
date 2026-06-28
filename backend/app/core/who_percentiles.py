"""WHO 2006 child growth standards — simplified percentile reference.

This module ships with a compact, interpolated version of the WHO 2006
standards for children 0-60 months. It supports:

- height-for-age (length/height)
- weight-for-age
- head-circumference-for-age
- BMI-for-age

For each indicator we store reference values at key ages for boys and girls.
Values between key ages are linearly interpolated.

The data are approximate reference centiles derived from the WHO Child Growth
Standards (2006). They are sufficient for MVP charting and alerts. In
production, replace the embedded tables with the official LMS parameter files
for exact z-score/percentile computation.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from dataclasses import dataclass

# Key ages in months for which we store reference values.
_AGE_KEYS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 18, 21, 24, 30, 36, 42, 48, 54, 60]

# Simplified reference centiles (P3, P15, P50, P85, P97) for each indicator.
# Values are approximate and derived from WHO 2006 growth charts.
# Units: height/cm, weight/kg, head_circumference/cm, bmi/kg/m^2.
_REFERENCE_TABLES: dict[str, dict[str, list[list[float]]]] = {
    "height": {
        "male": [
            [46.3, 48.0, 49.9, 51.7, 53.4],
            [50.8, 52.8, 54.7, 56.7, 58.6],
            [54.4, 56.4, 58.4, 60.4, 62.4],
            [57.1, 59.3, 61.4, 63.5, 65.5],
            [59.3, 61.6, 63.9, 66.1, 68.3],
            [61.1, 63.5, 65.9, 68.2, 70.4],
            [62.7, 65.1, 67.6, 70.0, 72.3],
            [64.1, 66.6, 69.2, 71.7, 74.1],
            [65.4, 68.0, 70.6, 73.2, 75.7],
            [66.7, 69.3, 72.0, 74.7, 77.3],
            [67.9, 70.5, 73.3, 76.0, 78.7],
            [69.0, 71.7, 74.5, 77.3, 80.0],
            [70.0, 72.8, 75.7, 78.6, 81.4],
            [72.9, 75.9, 79.1, 82.3, 85.4],
            [75.5, 78.8, 82.3, 85.7, 89.0],
            [77.8, 81.4, 85.1, 88.8, 92.4],
            [80.0, 83.8, 87.8, 91.7, 95.6],
            [84.3, 88.4, 92.7, 97.0, 101.2],
            [88.1, 92.4, 96.9, 101.4, 105.8],
            [91.3, 96.0, 100.8, 105.5, 110.2],
            [94.1, 99.1, 104.1, 109.1, 114.0],
            [96.7, 101.9, 107.2, 112.4, 117.6],
            [99.0, 104.6, 110.0, 115.5, 121.0],
        ],
        "female": [
            [45.6, 47.3, 49.1, 50.9, 52.7],
            [49.8, 51.7, 53.7, 55.6, 57.6],
            [53.2, 55.2, 57.1, 59.1, 61.1],
            [55.8, 57.9, 59.8, 61.9, 63.9],
            [57.9, 60.1, 62.2, 64.3, 66.4],
            [59.7, 61.9, 64.0, 66.2, 68.3],
            [61.2, 63.5, 65.7, 68.0, 70.2],
            [62.6, 64.9, 67.3, 69.6, 71.9],
            [63.9, 66.2, 68.7, 71.1, 73.5],
            [65.1, 67.5, 70.1, 72.6, 75.1],
            [66.3, 68.8, 71.5, 74.0, 76.6],
            [67.4, 70.0, 72.8, 75.4, 78.1],
            [68.6, 71.2, 74.0, 76.8, 79.7],
            [71.4, 74.3, 77.5, 80.6, 83.7],
            [74.1, 77.3, 80.9, 84.4, 87.9],
            [76.6, 80.2, 84.0, 87.8, 91.5],
            [78.7, 82.5, 86.4, 90.4, 94.3],
            [82.8, 86.9, 91.2, 95.5, 99.7],
            [86.5, 90.8, 95.2, 99.7, 104.1],
            [89.8, 94.3, 99.0, 103.7, 108.3],
            [92.7, 97.4, 102.3, 107.1, 111.9],
            [95.3, 100.3, 105.4, 110.5, 115.5],
            [97.7, 103.0, 108.2, 113.5, 118.7],
        ],
    },
    "weight": {
        "male": [
            [2.5, 2.9, 3.35, 3.8, 4.3],
            [3.4, 3.9, 4.47, 5.0, 5.7],
            [4.3, 4.9, 5.57, 6.3, 7.1],
            [4.9, 5.6, 6.38, 7.2, 8.0],
            [5.4, 6.1, 6.98, 7.8, 8.7],
            [5.7, 6.5, 7.46, 8.4, 9.4],
            [6.0, 6.9, 7.90, 8.9, 9.9],
            [6.3, 7.2, 8.30, 9.4, 10.5],
            [6.5, 7.5, 8.62, 9.8, 10.9],
            [6.7, 7.8, 8.90, 10.1, 11.3],
            [6.9, 8.0, 9.20, 10.5, 11.8],
            [7.0, 8.2, 9.45, 10.8, 12.1],
            [7.2, 8.4, 9.60, 11.0, 12.4],
            [7.7, 9.0, 10.30, 11.8, 13.3],
            [8.2, 9.5, 10.90, 12.5, 14.1],
            [8.6, 10.0, 11.50, 13.1, 14.8],
            [9.0, 10.5, 12.20, 13.9, 15.8],
            [9.8, 11.5, 13.30, 15.2, 17.3],
            [10.5, 12.4, 14.30, 16.4, 18.7],
            [11.2, 13.2, 15.30, 17.5, 20.0],
            [11.8, 14.0, 16.30, 18.7, 21.5],
            [12.4, 14.8, 17.30, 20.0, 23.0],
            [13.0, 15.5, 18.30, 21.2, 24.6],
        ],
        "female": [
            [2.4, 2.8, 3.23, 3.7, 4.2],
            [3.2, 3.7, 4.19, 4.7, 5.4],
            [4.0, 4.5, 5.13, 5.8, 6.6],
            [4.5, 5.1, 5.88, 6.6, 7.5],
            [5.0, 5.6, 6.38, 7.2, 8.1],
            [5.3, 6.0, 6.83, 7.7, 8.7],
            [5.6, 6.4, 7.30, 8.2, 9.3],
            [5.8, 6.6, 7.60, 8.6, 9.7],
            [6.0, 6.9, 7.90, 8.9, 10.0],
            [6.2, 7.1, 8.20, 9.3, 10.5],
            [6.4, 7.4, 8.50, 9.6, 10.8],
            [6.6, 7.6, 8.70, 9.9, 11.2],
            [6.8, 7.8, 8.90, 10.2, 11.5],
            [7.2, 8.4, 9.60, 11.0, 12.4],
            [7.6, 8.9, 10.20, 11.7, 13.3],
            [8.0, 9.4, 10.80, 12.4, 14.1],
            [8.4, 9.9, 11.50, 13.2, 15.1],
            [9.2, 10.8, 12.50, 14.4, 16.5],
            [9.9, 11.7, 13.50, 15.6, 17.9],
            [10.6, 12.5, 14.50, 16.8, 19.3],
            [11.3, 13.4, 15.60, 18.0, 20.7],
            [11.9, 14.2, 16.60, 19.2, 22.3],
            [12.5, 15.0, 17.70, 20.5, 23.9],
        ],
    },
    "head_circumference": {
        "male": [
            [31.7, 33.0, 34.5, 35.8, 37.0],
            [34.5, 35.7, 37.0, 38.3, 39.5],
            [36.3, 37.5, 38.7, 40.0, 41.2],
            [37.6, 38.8, 40.0, 41.3, 42.5],
            [38.7, 39.9, 41.1, 42.3, 43.5],
            [39.6, 40.8, 42.0, 43.2, 44.4],
            [40.4, 41.6, 42.8, 44.0, 45.2],
            [41.1, 42.3, 43.5, 44.7, 45.9],
            [41.8, 43.0, 44.2, 45.4, 46.6],
            [42.4, 43.6, 44.8, 46.0, 47.2],
            [43.0, 44.2, 45.4, 46.6, 47.8],
            [43.6, 44.7, 45.9, 47.1, 48.3],
            [44.1, 45.2, 46.4, 47.6, 48.8],
            [45.3, 46.5, 47.7, 48.9, 50.1],
            [46.2, 47.5, 48.8, 50.1, 51.4],
            [47.0, 48.3, 49.6, 51.0, 52.3],
            [47.6, 49.0, 50.4, 51.8, 53.2],
            [48.6, 50.0, 51.5, 53.0, 54.5],
            [49.4, 50.8, 52.3, 53.9, 55.4],
            [50.0, 51.5, 53.1, 54.7, 56.2],
            [50.5, 52.1, 53.7, 55.3, 56.9],
            [51.0, 52.6, 54.2, 55.8, 57.4],
            [51.4, 53.0, 54.6, 56.2, 57.8],
        ],
        "female": [
            [31.0, 32.4, 33.9, 35.2, 36.5],
            [33.8, 35.1, 36.4, 37.7, 39.0],
            [35.6, 36.8, 38.1, 39.4, 40.6],
            [36.9, 38.1, 39.4, 40.7, 41.9],
            [38.0, 39.2, 40.4, 41.7, 42.9],
            [38.9, 40.1, 41.3, 42.5, 43.7],
            [39.7, 40.9, 42.1, 43.3, 44.5],
            [40.4, 41.6, 42.8, 44.0, 45.2],
            [41.0, 42.2, 43.4, 44.6, 45.8],
            [41.6, 42.8, 44.0, 45.2, 46.4],
            [42.1, 43.3, 44.5, 45.7, 46.9],
            [42.6, 43.8, 45.0, 46.2, 47.4],
            [43.0, 44.2, 45.4, 46.6, 47.8],
            [44.1, 45.3, 46.5, 47.7, 48.9],
            [45.0, 46.2, 47.4, 48.6, 49.8],
            [45.8, 47.0, 48.2, 49.4, 50.6],
            [46.4, 47.6, 48.8, 50.0, 51.2],
            [47.3, 48.5, 49.7, 50.9, 52.1],
            [48.0, 49.2, 50.4, 51.6, 52.8],
            [48.6, 49.8, 51.0, 52.2, 53.4],
            [49.1, 50.3, 51.5, 52.7, 53.9],
            [49.6, 50.8, 52.0, 53.2, 54.4],
            [50.0, 51.2, 52.4, 53.6, 54.8],
        ],
    },
    "bmi": {
        "male": [
            [10.1, 11.5, 13.0, 14.4, 15.9],
            [10.8, 12.3, 13.9, 15.4, 17.0],
            [11.4, 13.0, 14.6, 16.2, 17.8],
            [11.9, 13.4, 15.1, 16.7, 18.3],
            [12.2, 13.7, 15.4, 17.0, 18.6],
            [12.4, 13.9, 15.5, 17.1, 18.7],
            [12.5, 14.0, 15.6, 17.2, 18.8],
            [12.6, 14.1, 15.7, 17.2, 18.8],
            [12.6, 14.1, 15.7, 17.2, 18.8],
            [12.6, 14.1, 15.7, 17.2, 18.8],
            [12.6, 14.1, 15.7, 17.2, 18.8],
            [12.6, 14.1, 15.6, 17.2, 18.8],
            [12.6, 14.1, 15.6, 17.2, 18.8],
            [12.5, 14.0, 15.6, 17.1, 18.7],
            [12.5, 13.9, 15.5, 17.0, 18.6],
            [12.4, 13.8, 15.4, 16.9, 18.4],
            [12.3, 13.7, 15.3, 16.8, 18.3],
            [12.2, 13.6, 15.1, 16.6, 18.1],
            [12.1, 13.5, 15.0, 16.5, 17.9],
            [12.1, 13.4, 14.9, 16.4, 17.8],
            [12.0, 13.4, 14.8, 16.3, 17.7],
            [12.0, 13.3, 14.8, 16.2, 17.6],
            [12.0, 13.3, 14.7, 16.2, 17.6],
        ],
        "female": [
            [10.0, 11.4, 12.9, 14.3, 15.8],
            [10.6, 12.1, 13.7, 15.2, 16.8],
            [11.2, 12.8, 14.4, 15.9, 17.5],
            [11.7, 13.2, 14.8, 16.4, 18.0],
            [12.0, 13.5, 15.1, 16.7, 18.3],
            [12.2, 13.7, 15.3, 16.9, 18.5],
            [12.3, 13.8, 15.4, 17.0, 18.6],
            [12.4, 13.9, 15.5, 17.1, 18.7],
            [12.4, 13.9, 15.5, 17.1, 18.7],
            [12.4, 13.9, 15.5, 17.1, 18.7],
            [12.4, 13.9, 15.5, 17.1, 18.7],
            [12.4, 13.9, 15.5, 17.1, 18.7],
            [12.4, 13.9, 15.5, 17.1, 18.7],
            [12.4, 13.9, 15.4, 17.0, 18.6],
            [12.3, 13.8, 15.4, 17.0, 18.5],
            [12.3, 13.8, 15.3, 16.9, 18.4],
            [12.2, 13.7, 15.2, 16.8, 18.3],
            [12.1, 13.6, 15.1, 16.6, 18.1],
            [12.1, 13.5, 15.0, 16.5, 18.0],
            [12.0, 13.4, 14.9, 16.4, 17.9],
            [12.0, 13.4, 14.8, 16.3, 17.8],
            [12.0, 13.3, 14.8, 16.2, 17.7],
            [11.9, 13.3, 14.7, 16.2, 17.6],
        ],
    },
}

_PERCENTILE_LABELS = [3, 15, 50, 85, 97]


def _interpolate_table(table: list[list[float]], age_months: float) -> list[float]:
    """Linearly interpolate a reference table at the given age in months."""
    if age_months <= _AGE_KEYS[0]:
        return table[0]
    if age_months >= _AGE_KEYS[-1]:
        return table[-1]

    idx = bisect_left(_AGE_KEYS, age_months)
    if _AGE_KEYS[idx] == age_months:
        return table[idx]

    age_low = _AGE_KEYS[idx - 1]
    age_high = _AGE_KEYS[idx]
    ratio = (age_months - age_low) / (age_high - age_low)
    low = table[idx - 1]
    high = table[idx]
    return [low[i] + ratio * (high[i] - low[i]) for i in range(len(_PERCENTILE_LABELS))]


def get_percentile_curve(
    indicator: str,
    sex: str,
    age_range_months: tuple[float, float] = (0, 60),
    step: float = 1.0,
) -> list[dict[str, float | int]]:
    """Return percentile curve points for charting.

    Each point contains age_months and P3/P15/P50/P85/P97 values.
    """
    indicator = indicator.lower()
    if indicator not in _REFERENCE_TABLES:
        raise ValueError(f"Unsupported indicator: {indicator}")
    sex_key = "male" if sex in ("male", "m", "男") else "female"
    table = _REFERENCE_TABLES[indicator][sex_key]

    start, end = age_range_months
    points = []
    age = start
    while age <= end:
        values = _interpolate_table(table, age)
        point: dict[str, float | int] = {"age_months": int(age)}
        for label, value in zip(_PERCENTILE_LABELS, values, strict=True):
            point[f"p{label}"] = round(value, 2)
        points.append(point)
        age += step
    return points


def estimate_percentile_and_zscore(
    indicator: str,
    sex: str,
    age_months: float,
    value: float,
) -> tuple[float | None, float | None]:
    """Estimate percentile and z-score from the simplified reference table.

    Uses inverse-CDF approximation: the value is interpolated between the
    surrounding percentile bands, then mapped to a standard normal z-score.
    """
    if age_months < 0 or age_months > 60:
        return None, None

    indicator = indicator.lower()
    if indicator not in _REFERENCE_TABLES:
        return None, None

    sex_key = "male" if sex in ("male", "m", "男") else "female"
    table = _REFERENCE_TABLES[indicator][sex_key]
    values = _interpolate_table(table, age_months)

    if value < values[0]:
        percentile = 1.0
    elif value > values[-1]:
        percentile = 99.0
    elif value == values[0]:
        percentile = 3.0
    elif value == values[-1]:
        percentile = 97.0
    else:
        # Find the two centile bands the value falls between.
        for i in range(len(_PERCENTILE_LABELS) - 1):
            low_val, high_val = values[i], values[i + 1]
            if low_val <= value <= high_val:
                low_p, high_p = _PERCENTILE_LABELS[i], _PERCENTILE_LABELS[i + 1]
                ratio = (value - low_val) / (high_val - low_val)
                percentile = low_p + ratio * (high_p - low_p)
                break
        else:
            percentile = 50.0

    # Map percentile to z-score using the inverse standard normal CDF.
    percentile_fraction = max(0.0001, min(0.9999, percentile / 100.0))
    z_score = _inverse_normal_cdf(percentile_fraction)
    return round(percentile, 1), round(z_score, 2)


def _inverse_normal_cdf(p: float) -> float:
    """Approximate inverse standard normal CDF (probit function).

    Uses the Acklam approximation, refined with one Halley iteration.
    """
    if p <= 0.0:
        return -5.0
    if p >= 1.0:
        return 5.0

    # Acklam coefficients
    a1 = -3.969683028665376e+01
    a2 = 2.209460984245205e+02
    a3 = -2.759285104469687e+02
    a4 = 1.383577518672690e+02
    a5 = -3.066479806614716e+01
    a6 = 2.506628277459239e+00

    b1 = -5.447609879822406e+01
    b2 = 1.615858368580409e+02
    b3 = -1.556989798598866e+02
    b4 = 6.680131188771972e+01
    b5 = -1.328068155288572e+01

    c1 = -7.784894002430293e-03
    c2 = -3.223964580411365e-01
    c3 = -2.400758277161838e+00
    c4 = -2.549732539343734e+00
    c5 = 4.374664141464968e+00
    c6 = 2.938163982698783e+00

    d1 = 7.784695709041462e-03
    d2 = 3.224671290700398e-01
    d3 = 2.445134137142996e+00
    d4 = 3.754408661907416e+00

    p_low = 0.02425
    p_high = 1.0 - p_low

    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        x = (((((c1 * q + c2) * q + c3) * q + c4) * q + c5) * q + c6) / (
            (((d1 * q + d2) * q + d3) * q + d4) * q + 1.0
        )
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        x = (((((a1 * r + a2) * r + a3) * r + a4) * r + a5) * r + a6) * q / (
            ((((b1 * r + b2) * r + b3) * r + b4) * r + b5) * r + 1.0
        )
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = -(((((c1 * q + c2) * q + c3) * q + c4) * q + c5) * q + c6) / (
            (((d1 * q + d2) * q + d3) * q + d4) * q + 1.0
        )

    # One Halley refinement iteration.
    e = 0.5 * math.erfc(-x / math.sqrt(2.0)) - p
    u = e * math.sqrt(2.0 * math.pi) * math.exp(x * x / 2.0)
    x = x - u / (1.0 + x * u / 2.0)
    return x


@dataclass(frozen=True)
class GrowthAssessment:
    percentile: float | None
    z_score: float | None
    status: str  # normal / watch / delayed / alert
    label: str


def assess_growth(
    indicator: str,
    sex: str,
    age_months: float,
    value: float,
) -> GrowthAssessment:
    """Return a human-readable growth assessment."""
    percentile, z_score = estimate_percentile_and_zscore(
        indicator, sex, age_months, value
    )
    if percentile is None or z_score is None:
        return GrowthAssessment(None, None, "unknown", "暂无评估数据")

    # Classify primarily by percentile; this avoids misleading z-scores when
    # the simplified reference table caps values at P3/P97.
    if percentile < 3 or percentile > 97:
        status = "alert"
        label = "明显偏离，建议就医"
    elif percentile < 15 or percentile > 85:
        status = "delayed"
        label = "偏离正常范围，建议关注"
    elif percentile < 25 or percentile > 75:
        status = "watch"
        label = "略有偏离，可继续观察"
    else:
        status = "normal"
        label = "处于正常范围"

    return GrowthAssessment(percentile, z_score, status, label)
