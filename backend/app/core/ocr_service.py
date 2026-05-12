from abc import ABC, abstractmethod
from typing import Optional
import re

from app.core.indicator_engine import IndicatorEngine


class OCRService(ABC):
    """Abstract OCR service for extracting health indicators from report images."""

    @abstractmethod
    async def extract_indicators(self, image_path: str) -> list[dict]:
        """
        Extract health indicators from an image.

        Returns list of dicts with keys: indicator_key, indicator_name, value, unit, raw_text
        """
        ...


class MockOCRService(OCRService):
    """Mock OCR for testing and dev environments without real OCR keys."""

    # Simulated text patterns for demo images
    PATTERNS = {
        r"收缩压[：:]\s*(\d+(?:\.\d+)?)": ("systolic_bp", "收缩压", "mmHg"),
        r"舒张压[：:]\s*(\d+(?:\.\d+)?)": ("diastolic_bp", "舒张压", "mmHg"),
        r"空腹血糖[：:]\s*(\d+(?:\.\d+)?)": ("fasting_glucose", "空腹血糖", "mmol/L"),
        r"血糖[：:]\s*(\d+(?:\.\d+)?)": ("fasting_glucose", "血糖", "mmol/L"),
        r"血红蛋白[：:]\s*(\d+(?:\.\d+)?)": ("hemoglobin", "血红蛋白", "g/L"),
        r"总胆固醇[：:]\s*(\d+(?:\.\d+)?)": ("total_cholesterol", "总胆固醇", "mmol/L"),
        r"低密度脂蛋白[：:]\s*(\d+(?:\.\d+)?)": ("ldl", "低密度脂蛋白", "mmol/L"),
        r"心率[：:]\s*(\d+(?:\.\d+)?)": ("heart_rate", "心率", "次/分"),
    }

    async def extract_indicators(self, image_path: str) -> list[dict]:
        # In mock mode, we simulate extraction based on filename hints
        results = []
        lower_path = image_path.lower()

        if "bp" in lower_path or "blood_pressure" in lower_path or "血压" in lower_path:
            results.append({
                "indicator_key": "systolic_bp",
                "indicator_name": "收缩压",
                "value": 125.0,
                "unit": "mmHg",
                "raw_text": "收缩压：125 mmHg",
            })
            results.append({
                "indicator_key": "diastolic_bp",
                "indicator_name": "舒张压",
                "value": 82.0,
                "unit": "mmHg",
                "raw_text": "舒张压：82 mmHg",
            })

        if "glucose" in lower_path or "血糖" in lower_path:
            results.append({
                "indicator_key": "fasting_glucose",
                "indicator_name": "空腹血糖",
                "value": 5.6,
                "unit": "mmol/L",
                "raw_text": "空腹血糖：5.6 mmol/L",
            })

        if "hb" in lower_path or "hemoglobin" in lower_path or "血红蛋白" in lower_path:
            results.append({
                "indicator_key": "hemoglobin",
                "indicator_name": "血红蛋白",
                "value": 135.0,
                "unit": "g/L",
                "raw_text": "血红蛋白：135 g/L",
            })

        if not results:
            # Default fallback
            results.append({
                "indicator_key": "systolic_bp",
                "indicator_name": "收缩压",
                "value": 120.0,
                "unit": "mmHg",
                "raw_text": "收缩压：120 mmHg",
            })

        return results


class RegexOCRService(OCRService):
    """Simple regex-based OCR that expects pre-extracted text.

    In production, this would be preceded by a real OCR engine like
    Tencent Cloud OCR, Baidu OCR, or Tesseract.
    """

    PATTERNS = {
        r"收缩压[\s:：]*(\d+(?:\.\d+)?)": ("systolic_bp", "收缩压", "mmHg"),
        r"舒张压[\s:：]*(\d+(?:\.\d+)?)": ("diastolic_bp", "舒张压", "mmHg"),
        r"空腹血糖[\s:：]*(\d+(?:\.\d+)?)": ("fasting_glucose", "空腹血糖", "mmol/L"),
        r"(?:^|[^a-zA-Z])血糖[\s:：]*(\d+(?:\.\d+)?)": ("fasting_glucose", "血糖", "mmol/L"),
        r"血红蛋白[\s:：]*(\d+(?:\.\d+)?)": ("hemoglobin", "血红蛋白", "g/L"),
        r"总胆固醇[\s:：]*(\d+(?:\.\d+)?)": ("total_cholesterol", "总胆固醇", "mmol/L"),
        r"低密度脂蛋白[\s:：]*(\d+(?:\.\d+)?)": ("ldl", "低密度脂蛋白", "mmol/L"),
        r"心率[\s:：]*(\d+(?:\.\d+)?)": ("heart_rate", "心率", "次/分"),
        r"BMI[\s:：]*(\d+(?:\.\d+)?)": ("bmi", "BMI", "kg/m²"),
    }

    async def extract_indicators(self, image_path: str) -> list[dict]:
        # For now, read a companion .txt file if it exists (simulating OCR text output)
        txt_path = image_path.rsplit(".", 1)[0] + ".txt"
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                text = f.read()
        except FileNotFoundError:
            # Fallback to mock
            svc = MockOCRService()
            return await svc.extract_indicators(image_path)

        results = []
        for pattern, (key, name, unit) in self.PATTERNS.items():
            for match in re.finditer(pattern, text, re.MULTILINE):
                try:
                    value = float(match.group(1))
                    results.append({
                        "indicator_key": key,
                        "indicator_name": name,
                        "value": value,
                        "unit": unit,
                        "raw_text": match.group(0),
                    })
                except (ValueError, IndexError):
                    continue

        # Deduplicate by key, keeping first match
        seen = set()
        unique = []
        for r in results:
            if r["indicator_key"] not in seen:
                seen.add(r["indicator_key"])
                unique.append(r)
        return unique


def get_ocr_service() -> OCRService:
    """Factory to get the configured OCR service."""
    import os
    if os.getenv("OCR_SERVICE", "mock").lower() == "regex":
        return RegexOCRService()
    return MockOCRService()
