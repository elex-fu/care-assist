from app.core.chronic_packages import (
    CHRONIC_PACKAGES,
    _generate_rule_summary,
    list_chronic_packages,
)
from app.schemas.chronic import ChronicIndicatorItem


class TestChronicPackages:
    def test_list_packages(self):
        packages = list_chronic_packages()
        assert len(packages) == 3
        keys = {p.package for p in packages}
        assert keys == {"hypertension", "diabetes", "dyslipidemia"}

    def test_packages_configured(self):
        assert "hypertension" in CHRONIC_PACKAGES
        assert "systolic_bp" in CHRONIC_PACKAGES["hypertension"]["indicator_keys"]

    def test_rule_summary_critical(self):
        indicators = [
            ChronicIndicatorItem(
                key="systolic_bp",
                name="收缩压",
                value=200,
                unit="mmHg",
                status="critical",
                ref_range="90-140 mmHg",
            ),
            ChronicIndicatorItem(
                key="diastolic_bp",
                name="舒张压",
                value=80,
                unit="mmHg",
                status="normal",
                ref_range="60-90 mmHg",
            ),
        ]
        summary = _generate_rule_summary("hypertension", indicators)
        assert "收缩压" in summary
        assert "危急" in summary or "尽快就医" in summary

    def test_rule_summary_abnormal(self):
        indicators = [
            ChronicIndicatorItem(
                key="fasting_glucose",
                name="空腹血糖",
                value=8.0,
                unit="mmol/L",
                status="high",
                ref_range="3.9-6.1 mmol/L",
            ),
        ]
        summary = _generate_rule_summary("diabetes", indicators)
        assert "空腹血糖" in summary
        assert "偏离" in summary or "咨询医生" in summary

    def test_rule_summary_normal(self):
        indicators = [
            ChronicIndicatorItem(
                key="total_cholesterol",
                name="总胆固醇",
                value=4.5,
                unit="mmol/L",
                status="normal",
                ref_range="0-5.2 mmol/L",
            ),
            ChronicIndicatorItem(
                key="ldl",
                name="低密度脂蛋白",
                value=2.5,
                unit="mmol/L",
                status="normal",
                ref_range="0-3.4 mmol/L",
            ),
        ]
        summary = _generate_rule_summary("dyslipidemia", indicators)
        assert "正常" in summary

    def test_rule_summary_no_data(self):
        indicators = [
            ChronicIndicatorItem(
                key="systolic_bp",
                name="收缩压",
                value=None,
                unit="mmHg",
                status="no_data",
                ref_range="90-140 mmHg",
            ),
            ChronicIndicatorItem(
                key="diastolic_bp",
                name="舒张压",
                value=None,
                unit="mmHg",
                status="no_data",
                ref_range="60-90 mmHg",
            ),
        ]
        summary = _generate_rule_summary("hypertension", indicators)
        assert "未记录" in summary
