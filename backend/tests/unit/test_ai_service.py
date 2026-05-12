import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.ai_service import AIService


class TestAIServiceMockReplies:
    async def test_greeting_response(self):
        svc = AIService()
        member = MagicMock()
        member.name = "测试成员"
        member.type = "adult"
        reply = await svc.generate_reply(
            member=member,
            conversation_history=[],
            user_message="你好",
        )
        assert "您好" in reply
        assert "测试成员" in reply

    async def test_indicator_analysis_no_data(self):
        svc = AIService()
        member = MagicMock()
        member.name = "张三"
        reply = await svc.generate_reply(
            member=member,
            conversation_history=[],
            user_message="血压怎么样",
        )
        assert "还没有记录" in reply or "建议定期记录" in reply

    async def test_indicator_analysis_with_normal_data(self):
        svc = AIService()
        member = MagicMock()
        member.name = "张三"
        indicators = [
            {"indicator_name": "收缩压", "value": 120, "unit": "mmHg", "status": "normal"}
        ]
        reply = await svc.generate_reply(
            member=member,
            conversation_history=[],
            user_message="血压正常吗",
            recent_indicators=indicators,
        )
        assert "正常" in reply
        assert "120" in reply

    async def test_indicator_analysis_with_abnormal_data(self):
        svc = AIService()
        member = MagicMock()
        member.name = "张三"
        indicators = [
            {"indicator_name": "收缩压", "value": 150, "unit": "mmHg", "status": "high", "indicator_key": "systolic_bp"}
        ]
        reply = await svc.generate_reply(
            member=member,
            conversation_history=[],
            user_message="血压高吗",
            recent_indicators=indicators,
        )
        assert "偏高" in reply or "异常" in reply
        assert "150" in reply

    async def test_diet_advice_for_elderly(self):
        svc = AIService()
        member = MagicMock()
        member.name = "李奶奶"
        member.type = "elderly"
        reply = await svc.generate_reply(
            member=member,
            conversation_history=[],
            user_message="饮食要注意什么",
        )
        assert "建议" in reply
        assert "李奶奶" in reply

    async def test_diet_advice_with_high_bp(self):
        svc = AIService()
        member = MagicMock()
        member.name = "张三"
        member.type = "adult"
        indicators = [
            {"indicator_key": "systolic_bp", "status": "high", "value": 150, "unit": "mmHg"}
        ]
        reply = await svc.generate_reply(
            member=member,
            conversation_history=[],
            user_message="有什么建议",
            recent_indicators=indicators,
        )
        assert "血压" in reply or "低盐" in reply

    async def test_trend_analysis_insufficient_data(self):
        svc = AIService()
        member = MagicMock()
        member.name = "张三"
        reply = await svc.generate_reply(
            member=member,
            conversation_history=[],
            user_message="最近变化趋势",
            recent_indicators=[
                {"indicator_key": "systolic_bp", "value": 120, "unit": "mmHg"}
            ],
        )
        assert "不够多" in reply or "持续记录" in reply

    async def test_trend_analysis_with_data(self):
        svc = AIService()
        member = MagicMock()
        member.name = "张三"
        indicators = [
            {"indicator_key": "systolic_bp", "indicator_name": "收缩压", "value": 125, "unit": "mmHg", "status": "normal"},
            {"indicator_key": "systolic_bp", "indicator_name": "收缩压", "value": 120, "unit": "mmHg", "status": "normal"},
        ]
        reply = await svc.generate_reply(
            member=member,
            conversation_history=[],
            user_message="最近趋势",
            recent_indicators=indicators,
        )
        assert "收缩压" in reply
        assert "125" in reply or "120" in reply

    async def test_report_analysis(self):
        svc = AIService()
        member = MagicMock()
        member.name = "张三"
        reports = [
            {"type": "lab", "ocr_status": "completed", "extracted_indicators": [
                {"indicator_key": "systolic_bp", "value": 120, "status": "normal"}
            ]}
        ]
        reply = await svc.generate_reply(
            member=member,
            conversation_history=[],
            user_message="报告解读",
            recent_reports=reports,
        )
        assert "报告" in reply
        assert "指标" in reply or "正常" in reply

    async def test_default_response(self):
        svc = AIService()
        member = MagicMock()
        member.name = "张三"
        reply = await svc.generate_reply(
            member=member,
            conversation_history=[],
            user_message="随便说点什么",
        )
        assert "分析" in reply or "了解" in reply

    async def test_api_key_calls_llm(self, monkeypatch):
        monkeypatch.setenv("AI_API_KEY", "fake-key")
        svc = AIService()
        member = MagicMock()
        member.name = "张三"
        reply = await svc.generate_reply(
            member=member,
            conversation_history=[],
            user_message="测试",
        )
        assert "[AI]" in reply

    async def test_family_summary_normal(self):
        svc = AIService()
        cards = [
            {"name": "张三", "latest_status": "normal", "abnormal_count": 0},
            {"name": "李四", "latest_status": "normal", "abnormal_count": 0},
        ]
        summary = await svc.generate_family_summary(cards)
        assert "整体平稳" in summary or "良好" in summary
        assert "免责声明" in summary

    async def test_family_summary_with_abnormal(self):
        svc = AIService()
        cards = [
            {"name": "张三", "latest_status": "normal", "abnormal_count": 0},
            {"name": "李四", "latest_status": "high", "abnormal_count": 2},
        ]
        summary = await svc.generate_family_summary(cards)
        assert "李四" in summary
        assert "免责声明" in summary

    async def test_family_summary_critical(self):
        svc = AIService()
        cards = [
            {"name": "张三", "latest_status": "critical", "abnormal_count": 1},
        ]
        summary = await svc.generate_family_summary(cards)
        assert "严重异常" in summary or "就医" in summary
        assert "免责声明" in summary

    async def test_disclaimer_in_all_replies(self):
        svc = AIService()
        member = MagicMock()
        member.name = "张三"
        member.type = "adult"
        test_cases = [
            ("你好", "您好"),
            ("血压怎么样", "还没有记录"),
            ("饮食要注意什么", "建议"),
            ("随便说点什么", "分析"),
        ]
        for msg, expected in test_cases:
            reply = await svc.generate_reply(
                member=member,
                conversation_history=[],
                user_message=msg,
            )
            assert "免责声明" in reply, f"Missing disclaimer for message: {msg}"
            assert expected in reply, f"Missing expected content for message: {msg}"
