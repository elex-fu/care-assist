import pytest
from unittest.mock import MagicMock

from app.core.ai_service import AIService


def test_rule_based_summary_no_indicators():
    member = MagicMock()
    member.name = "李四"
    report = MagicMock()
    report.type = "lab"
    report.extracted_indicators = []
    svc = AIService()
    text = svc._rule_based_summary(member, report, [])
    assert "暂未识别" in text


def test_rule_based_summary_abnormal():
    member = MagicMock()
    member.name = "李四"
    report = MagicMock()
    report.type = "lab"
    extracted = [
        {"indicator_name": "血压", "value": 150, "unit": "mmHg", "status": "high"},
        {"indicator_name": "血糖", "value": 5.5, "unit": "mmol/L", "status": "normal"},
    ]
    svc = AIService()
    text = svc._rule_based_summary(member, report, extracted)
    assert "血压" in text
    assert "异常" in text


def test_rule_based_summary_normal():
    member = MagicMock()
    member.name = "李四"
    report = MagicMock()
    report.type = "lab"
    extracted = [
        {"indicator_name": "血压", "value": 120, "unit": "mmHg", "status": "normal"},
    ]
    svc = AIService()
    text = svc._rule_based_summary(member, report, extracted)
    assert "参考范围" in text
