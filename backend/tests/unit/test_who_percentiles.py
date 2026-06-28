import pytest

from app.core.who_percentiles import (
    assess_growth,
    estimate_percentile_and_zscore,
    get_percentile_curve,
)


@pytest.mark.parametrize(
    "indicator,sex,age_months,value",
    [
        ("height", "male", 12, 75.7),
        ("weight", "female", 12, 8.9),
        ("head_circumference", "male", 12, 46.4),
        ("bmi", "male", 12, 15.6),
    ],
)
def test_estimate_percentile_near_median(indicator, sex, age_months, value):
    percentile, z_score = estimate_percentile_and_zscore(
        indicator, sex, age_months, value
    )
    assert percentile is not None
    assert 45 <= percentile <= 55
    assert -0.5 <= z_score <= 0.5


def test_get_percentile_curve_returns_expected_keys():
    curve = get_percentile_curve("height", "male", age_range_months=(0, 12), step=3)
    assert len(curve) == 5
    assert all({"age_months", "p3", "p15", "p50", "p85", "p97"} <= set(point) for point in curve)
    assert curve[0]["p3"] < curve[0]["p50"] < curve[0]["p97"]


def test_assess_growth_normal():
    result = assess_growth("height", "male", 12, 75.7)
    assert result.status == "normal"
    assert result.percentile is not None


def test_assess_growth_delayed():
    result = assess_growth("height", "male", 12, 60.0)
    assert result.status in {"delayed", "alert"}


def test_assess_growth_alert():
    result = assess_growth("height", "male", 12, 50.0)
    assert result.status == "alert"
