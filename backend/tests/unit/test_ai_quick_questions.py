import pytest
from unittest.mock import MagicMock

from app.core.ai_service import AIService


@pytest.mark.asyncio
async def test_rule_based_quick_questions():
    member = MagicMock()
    member.name = "张三"
    svc = AIService()
    qs = svc._rule_based_quick_questions(member, "pages/home/home", [], [])
    assert any("张三" in q for q in qs)
    assert len(qs) <= 4


@pytest.mark.asyncio
async def test_rule_based_quick_questions_with_context():
    member = MagicMock()
    member.name = "李四"
    svc = AIService()
    qs = svc._rule_based_quick_questions(
        member,
        "pages/indicators/indicators",
        [{"indicator_key": "systolic_bp"}],
        [{"id": "r1"}],
    )
    assert any("李四" in q for q in qs)
    assert any("指标" in q for q in qs)
    assert any("报告" in q for q in qs)


@pytest.mark.asyncio
async def test_generate_quick_questions_falls_back_when_no_provider():
    member = MagicMock()
    member.name = "王五"
    svc = AIService()
    qs = await svc.generate_quick_questions(member, "pages/home/home", [], [])
    assert any("王五" in q for q in qs)
