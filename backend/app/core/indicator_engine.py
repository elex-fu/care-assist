from typing import Optional


class IndicatorEngine:
    THRESHOLDS = {
        "systolic_bp": {
            "name": "收缩压",
            "unit": "mmHg",
            "threshold": {"lower": 90, "upper": 140},
            "age_groups": [
                {"max_age_months": 144, "lower": 90, "upper": 120},
                {"max_age_months": 720, "lower": 90, "upper": 140},
                {"max_age_months": 99999, "lower": 90, "upper": 150},
            ],
        },
        "diastolic_bp": {
            "name": "舒张压",
            "unit": "mmHg",
            "threshold": {"lower": 60, "upper": 90},
        },
        "fasting_glucose": {
            "name": "空腹血糖",
            "unit": "mmol/L",
            "threshold": {"lower": 3.9, "upper": 6.1},
        },
        "hemoglobin": {
            "name": "血红蛋白",
            "unit": "g/L",
            "threshold": {"lower": 120, "upper": 160},
            "age_groups": [
                {"max_age_months": 12, "lower": 100, "upper": 140},
                {"max_age_months": 144, "lower": 110, "upper": 145},
                {"max_age_months": 720, "lower": 120, "upper": 160},
                {"max_age_months": 99999, "lower": 110, "upper": 160},
            ],
        },
        "total_cholesterol": {
            "name": "总胆固醇",
            "unit": "mmol/L",
            "threshold": {"lower": 0, "upper": 5.2},
        },
        "ldl": {
            "name": "低密度脂蛋白",
            "unit": "mmol/L",
            "threshold": {"lower": 0, "upper": 3.4},
        },
        "heart_rate": {
            "name": "心率",
            "unit": "次/分",
            "threshold": {"lower": 60, "upper": 100},
        },
        "bmi": {
            "name": "BMI",
            "unit": "kg/m²",
            "threshold": {"lower": 18.5, "upper": 24},
        },
    }

    NAME_MAPPING = {
        "血压（收缩压）": "systolic_bp",
        "收缩压": "systolic_bp",
        "SBP": "systolic_bp",
        "血压（舒张压）": "diastolic_bp",
        "舒张压": "diastolic_bp",
        "DBP": "diastolic_bp",
        "空腹血糖": "fasting_glucose",
        "血糖": "fasting_glucose",
        "血红蛋白": "hemoglobin",
        "总胆固醇": "total_cholesterol",
        "胆固醇": "total_cholesterol",
        "低密度脂蛋白": "ldl",
        "心率": "heart_rate",
        "BMI": "bmi",
    }

    @classmethod
    def standardize(cls, raw_name: str, raw_unit: str) -> dict:
        key = cls.NAME_MAPPING.get(raw_name.strip())
        if not key:
            key = f"custom_{hash(raw_name) & 0xFFFFFFFF}"
        config = cls.THRESHOLDS.get(key, {})
        return {
            "key": key,
            "display_name": config.get("name", raw_name),
            "unit": cls._normalize_unit(raw_unit),
        }

    @classmethod
    def _normalize_unit(cls, unit: str) -> str:
        u = unit.strip().lower()
        mappings = {
            "mmhg": "mmHg",
            "mmol/l": "mmol/L",
            "mmol/l": "mmol/L",
            "g/l": "g/L",
            "kg/m2": "kg/m²",
            "kg/m²": "kg/m²",
        }
        return mappings.get(u, unit)

    @classmethod
    def judge(cls, value: float, indicator_key: str, age_months: Optional[int] = None) -> str:
        config = cls.THRESHOLDS.get(indicator_key)
        if not config:
            return "unknown"

        threshold = config["threshold"]
        if age_months and "age_groups" in config:
            for group in config["age_groups"]:
                if age_months <= group["max_age_months"]:
                    threshold = group
                    break

        lower = threshold.get("lower")
        upper = threshold.get("upper")

        # Critical: 30% deviation from range
        if lower is not None and value < lower * 0.7:
            return "critical"
        if upper is not None and value > upper * 1.3:
            return "critical"

        if lower is not None and value < lower:
            return "low"
        if upper is not None and value > upper:
            return "high"

        return "normal"

    @classmethod
    def calculate_deviation(cls, value: float, indicator_key: str, age_months: Optional[int] = None) -> float:
        config = cls.THRESHOLDS.get(indicator_key)
        if not config:
            return 0.0

        threshold = config["threshold"]
        if age_months and "age_groups" in config:
            for group in config["age_groups"]:
                if age_months <= group["max_age_months"]:
                    threshold = group
                    break

        lower = threshold.get("lower")
        upper = threshold.get("upper")

        if lower is not None and value < lower:
            return (value - lower) / lower
        if upper is not None and value > upper:
            return (value - upper) / upper
        return 0.0

    @classmethod
    def evaluate_trend(cls, current: float, previous: float, indicator_key: str) -> dict:
        change = current - previous
        change_pct = abs(change / previous) if previous else 0

        direction = "stable" if change_pct < 0.05 else ("up" if change > 0 else "down")
        magnitude = "small" if change_pct < 0.1 else ("moderate" if change_pct < 0.3 else "large")

        is_lower_better = indicator_key in ["fasting_glucose", "ldl", "total_cholesterol", "triglycerides"]
        if is_lower_better:
            evaluation = "improving" if direction == "down" else ("worsening" if direction == "up" else "stable")
        else:
            evaluation = "improving" if direction == "up" else ("worsening" if direction == "down" else "stable")

        return {"direction": direction, "magnitude": magnitude, "evaluation": evaluation}
