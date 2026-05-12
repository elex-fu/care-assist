import pytest
import tempfile
import os

from app.core.ocr_service import MockOCRService, RegexOCRService, get_ocr_service


class TestMockOCRService:
    async def test_extract_bp_indicators(self):
        svc = MockOCRService()
        results = await svc.extract_indicators("/uploads/bp_report.jpg")
        assert len(results) == 2
        keys = {r["indicator_key"] for r in results}
        assert "systolic_bp" in keys
        assert "diastolic_bp" in keys

    async def test_extract_glucose_indicator(self):
        svc = MockOCRService()
        results = await svc.extract_indicators("/uploads/glucose_血糖.jpg")
        assert any(r["indicator_key"] == "fasting_glucose" for r in results)

    async def test_fallback_default(self):
        svc = MockOCRService()
        results = await svc.extract_indicators("/uploads/unknown.jpg")
        assert len(results) >= 1
        assert results[0]["indicator_key"] == "systolic_bp"

    async def test_extracted_values_are_numeric(self):
        svc = MockOCRService()
        results = await svc.extract_indicators("/uploads/bp_report.jpg")
        for r in results:
            assert isinstance(r["value"], float)
            assert r["unit"]
            assert r["raw_text"]


class TestRegexOCRService:
    async def test_extract_from_text_file(self):
        svc = RegexOCRService()
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = os.path.join(tmpdir, "report.jpg")
            txt_path = os.path.join(tmpdir, "report.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("收缩压：145 mmHg\n舒张压：90 mmHg\n")

            results = await svc.extract_indicators(img_path)

        assert len(results) == 2
        sbp = next(r for r in results if r["indicator_key"] == "systolic_bp")
        assert sbp["value"] == 145.0
        dbp = next(r for r in results if r["indicator_key"] == "diastolic_bp")
        assert dbp["value"] == 90.0

    async def test_fallback_to_mock_when_no_text_file(self):
        svc = RegexOCRService()
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = os.path.join(tmpdir, "only_image.jpg")
            results = await svc.extract_indicators(img_path)

        assert len(results) >= 1
        assert results[0]["indicator_key"] == "systolic_bp"

    async def test_deduplicates_by_key(self):
        svc = RegexOCRService()
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = os.path.join(tmpdir, "dup.jpg")
            txt_path = os.path.join(tmpdir, "dup.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("收缩压：120\n收缩压：125\n")

            results = await svc.extract_indicators(img_path)

        sbp_results = [r for r in results if r["indicator_key"] == "systolic_bp"]
        assert len(sbp_results) == 1
        assert sbp_results[0]["value"] == 120.0


class TestOCRServiceFactory:
    def test_default_returns_mock(self):
        svc = get_ocr_service()
        assert isinstance(svc, MockOCRService)

    def test_regex_env_returns_regex(self, monkeypatch):
        monkeypatch.setenv("OCR_SERVICE", "regex")
        svc = get_ocr_service()
        assert isinstance(svc, RegexOCRService)
