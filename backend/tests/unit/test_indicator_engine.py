import pytest

from app.core.indicator_engine import IndicatorEngine


class TestStandardize:
    def test_known_name_mapping(self):
        result = IndicatorEngine.standardize("收缩压", "mmHg")
        assert result["key"] == "systolic_bp"
        assert result["display_name"] == "收缩压"
        assert result["unit"] == "mmHg"

    def test_sbp_alias(self):
        result = IndicatorEngine.standardize("SBP", "mmHg")
        assert result["key"] == "systolic_bp"

    def test_unknown_name_returns_custom(self):
        result = IndicatorEngine.standardize("未知指标", "xxx")
        assert result["key"].startswith("custom_")
        assert result["display_name"] == "未知指标"


class TestJudge:
    def test_normal_value(self):
        assert IndicatorEngine.judge(120, "systolic_bp", age_months=360) == "normal"

    def test_high_value(self):
        assert IndicatorEngine.judge(150, "systolic_bp", age_months=360) == "high"

    def test_critical_value(self):
        assert IndicatorEngine.judge(200, "systolic_bp", age_months=360) == "critical"

    def test_low_value(self):
        assert IndicatorEngine.judge(70, "systolic_bp", age_months=360) == "low"

    def test_age_group_threshold(self):
        # Child threshold: upper 120
        assert IndicatorEngine.judge(125, "systolic_bp", age_months=100) == "high"
        # Adult threshold: upper 140
        assert IndicatorEngine.judge(125, "systolic_bp", age_months=360) == "normal"

    def test_unknown_indicator(self):
        assert IndicatorEngine.judge(100, "unknown_key") == "unknown"


class TestCalculateDeviation:
    def test_normal_returns_zero(self):
        assert IndicatorEngine.calculate_deviation(120, "systolic_bp", age_months=360) == 0.0

    def test_high_deviation(self):
        # Upper 140, value 150 -> (150-140)/140 = ~0.071
        dev = IndicatorEngine.calculate_deviation(150, "systolic_bp", age_months=360)
        assert pytest.approx(dev, 0.01) == 0.0714

    def test_low_deviation(self):
        # Lower 90, value 80 -> (80-90)/90 = -0.111
        dev = IndicatorEngine.calculate_deviation(80, "systolic_bp", age_months=360)
        assert pytest.approx(dev, 0.01) == -0.1111


class TestEvaluateTrend:
    def test_stable(self):
        result = IndicatorEngine.evaluate_trend(120, 121, "systolic_bp")
        assert result["direction"] == "stable"
        assert result["evaluation"] == "stable"

    def test_improving_lower_is_better(self):
        result = IndicatorEngine.evaluate_trend(5.0, 6.0, "fasting_glucose")
        assert result["direction"] == "down"
        assert result["evaluation"] == "improving"

    def test_worsening(self):
        result = IndicatorEngine.evaluate_trend(6.5, 6.0, "fasting_glucose")
        assert result["direction"] == "up"
        assert result["evaluation"] == "worsening"
