"""Seed data for care-assist."""

from sqlalchemy.ext.asyncio import AsyncSession

THRESHOLDS = {
    "systolic_bp": {
        "name": "收缩压",
        "unit": "mmHg",
        "thresholds": {
            "default": {"lower": 90, "upper": 140},
            "age_groups": [
                {"max_age_months": 144, "lower": 90, "upper": 120},
                {"max_age_months": 720, "lower": 90, "upper": 140},
                {"max_age_months": 99999, "lower": 90, "upper": 150},
            ],
        },
    },
    "diastolic_bp": {
        "name": "舒张压",
        "unit": "mmHg",
        "thresholds": {
            "default": {"lower": 60, "upper": 90},
            "age_groups": [
                {"max_age_months": 144, "lower": 60, "upper": 80},
                {"max_age_months": 720, "lower": 60, "upper": 90},
                {"max_age_months": 99999, "lower": 60, "upper": 90},
            ],
        },
    },
    "fasting_glucose": {
        "name": "空腹血糖",
        "unit": "mmol/L",
        "thresholds": {
            "default": {"lower": 3.9, "upper": 6.1},
        },
    },
    "hemoglobin": {
        "name": "血红蛋白",
        "unit": "g/L",
        "thresholds": {
            "default": {"lower": 120, "upper": 160},
            "age_groups": [
                {"max_age_months": 12, "lower": 100, "upper": 140},
                {"max_age_months": 144, "lower": 110, "upper": 145},
                {"max_age_months": 720, "lower": 120, "upper": 160},
                {"max_age_months": 99999, "lower": 110, "upper": 160},
            ],
        },
    },
    "total_cholesterol": {
        "name": "总胆固醇",
        "unit": "mmol/L",
        "thresholds": {
            "default": {"lower": 0, "upper": 5.2},
        },
    },
    "ldl": {
        "name": "低密度脂蛋白",
        "unit": "mmol/L",
        "thresholds": {
            "default": {"lower": 0, "upper": 3.4},
        },
    },
    "heart_rate": {
        "name": "心率",
        "unit": "次/分",
        "thresholds": {
            "default": {"lower": 60, "upper": 100},
        },
    },
    "bmi": {
        "name": "BMI",
        "unit": "kg/m²",
        "thresholds": {
            "default": {"lower": 18.5, "upper": 24},
        },
    },
    "waist_circumference": {
        "name": "腰围",
        "unit": "cm",
        "thresholds": {
            "default": {"lower": 0, "upper": 90},
        },
    },
}

VACCINE_SCHEDULE = [
    {"name": "乙肝疫苗", "doses": [
        {"dose": 1, "scheduled_months": 0},
        {"dose": 2, "scheduled_months": 1},
        {"dose": 3, "scheduled_months": 6},
    ]},
    {"name": "卡介苗", "doses": [
        {"dose": 1, "scheduled_months": 0},
    ]},
    {"name": "脊髓灰质炎疫苗", "doses": [
        {"dose": 1, "scheduled_months": 2},
        {"dose": 2, "scheduled_months": 3},
        {"dose": 3, "scheduled_months": 4},
        {"dose": 4, "scheduled_months": 48},
    ]},
    {"name": "百白破疫苗", "doses": [
        {"dose": 1, "scheduled_months": 3},
        {"dose": 2, "scheduled_months": 4},
        {"dose": 3, "scheduled_months": 5},
        {"dose": 4, "scheduled_months": 18},
        {"dose": 5, "scheduled_months": 72},
    ]},
    {"name": "麻腮风疫苗", "doses": [
        {"dose": 1, "scheduled_months": 8},
        {"dose": 2, "scheduled_months": 18},
    ]},
    {"name": "乙脑疫苗", "doses": [
        {"dose": 1, "scheduled_months": 8},
        {"dose": 2, "scheduled_months": 24},
    ]},
    {"name": "甲肝疫苗", "doses": [
        {"dose": 1, "scheduled_months": 18},
        {"dose": 2, "scheduled_months": 24},
    ]},
    {"name": "A群流脑疫苗", "doses": [
        {"dose": 1, "scheduled_months": 6},
        {"dose": 2, "scheduled_months": 9},
    ]},
    {"name": "A+C群流脑疫苗", "doses": [
        {"dose": 1, "scheduled_months": 36},
        {"dose": 2, "scheduled_months": 72},
    ]},
]


async def seed_all(db: AsyncSession) -> None:
    """Run all seeders. Idempotent."""
    # Thresholds and vaccine schedules are static dictionaries used by services.
    # No DB inserts needed for them in Phase 1.
    pass
