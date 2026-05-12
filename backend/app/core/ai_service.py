import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.indicator_engine import IndicatorEngine
from app.models.member import Member


class AIService:
    """AI health assistant service with rule-based responses for MVP.
    In production, this would call a real LLM API (OpenAI, Claude, etc.)
    """

    SYSTEM_PROMPT = """你是一位家庭智能健康助手，擅长解读健康指标和医疗报告。
请用简洁、温暖的中文回答，给出具体、可操作的建议。
如果指标异常，请提醒用户关注并建议就医。

免责声明：本助手的建议仅供参考，不能替代专业医生的诊断和治疗。如有严重不适，请及时就医。"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("AI_API_KEY")

    async def generate_reply(
        self,
        member: Member,
        conversation_history: list[dict],
        user_message: str,
        page_context: Optional[str] = None,
        recent_indicators: Optional[list[dict]] = None,
        recent_reports: Optional[list[dict]] = None,
    ) -> str:
        """Generate AI reply based on member health data and user message."""

        # If real API key is configured, use it
        if self.api_key:
            return await self._call_llm_api(
                member, conversation_history, user_message,
                page_context, recent_indicators, recent_reports
            )

        # Otherwise use rule-based mock responses
        return await self._generate_mock_reply(
            member, user_message, page_context, recent_indicators, recent_reports
        )

    async def _call_llm_api(
        self, member, history, message, page_context, indicators, reports
    ) -> str:
        # Placeholder for real LLM integration
        # In production: call OpenAI/Claude/ERNIE API
        context = self._build_context(member, indicators, reports)
        return f"[AI] 收到您的问题：{message}。根据{member.name}的健康数据，{context}"

    def _append_disclaimer(self, reply: str) -> str:
        disclaimer = "\n\n【免责声明】本助手的建议仅供参考，不能替代专业医生的诊断和治疗。如有严重不适，请及时就医。"
        if disclaimer not in reply:
            reply += disclaimer
        return reply

    async def _generate_mock_reply(
        self,
        member: Member,
        user_message: str,
        page_context: Optional[str],
        recent_indicators: Optional[list[dict]],
        recent_reports: Optional[list[dict]],
    ) -> str:
        user_lower = user_message.lower()

        # Greeting patterns
        if any(w in user_lower for w in ["你好", "hello", "hi", "在吗"]):
            reply = f"您好！我是您的家庭健康助手。{member.name}最近的身体状况如何？我可以帮您分析健康指标或解读检查报告。"
            return self._append_disclaimer(reply)

        # Indicator analysis
        if any(w in user_lower for w in ["血压", "血糖", "指标", "正常吗", "怎么样"]):
            if recent_indicators:
                reply = self._analyze_indicators(member.name, recent_indicators)
            else:
                reply = f"目前{member.name}还没有记录健康指标。建议定期记录血压、血糖等关键指标，我可以帮您分析趋势。"
            return self._append_disclaimer(reply)

        # Report analysis
        if any(w in user_lower for w in ["报告", "检查", "ocr", "化验"]):
            if recent_reports:
                reply = self._analyze_reports(member.name, recent_reports)
            else:
                reply = f"目前{member.name}还没有上传检查报告。您可以上传化验单或诊断报告，我会帮您提取关键指标并解读。"
            return self._append_disclaimer(reply)

        # Trend analysis
        if any(w in user_lower for w in ["趋势", "变化", "最近", "恶化", "改善"]):
            if recent_indicators and len(recent_indicators) >= 2:
                reply = self._analyze_trends(member.name, recent_indicators)
            else:
                reply = f"需要至少两条指标记录才能分析趋势。建议持续记录{member.name}的健康数据。"
            return self._append_disclaimer(reply)

        # Diet / lifestyle advice
        if any(w in user_lower for w in ["饮食", "吃", "运动", "注意", "建议"]):
            reply = self._give_advice(member, recent_indicators)
            return self._append_disclaimer(reply)

        # Default response
        reply = (
            f"我理解您关于{member.name}的关心。"
            "我可以帮您：\n"
            "1. 分析健康指标（血压、血糖等）\n"
            "2. 解读检查报告\n"
            "3. 提供健康建议\n"
            "请告诉我您想了解哪方面的信息？"
        )
        return self._append_disclaimer(reply)

    def _analyze_indicators(self, name: str, indicators: list[dict]) -> str:
        abnormal = [i for i in indicators if i.get("status") in ("low", "high", "critical")]
        if not abnormal:
            latest = indicators[0]
            return (
                f"{name}的{latest.get('indicator_name', '指标')}目前处于正常范围"
                f"（{latest.get('value')} {latest.get('unit')}），"
                f"继续保持良好的生活习惯！"
            )

        msgs = []
        for ind in abnormal[:3]:
            status_map = {
                "low": "偏低",
                "high": "偏高",
                "critical": "严重异常",
            }
            msgs.append(
                f"{ind.get('indicator_name')} {status_map.get(ind['status'], '异常')}"
                f"（{ind.get('value')} {ind.get('unit')}）"
            )
        msg = "、".join(msgs)
        return (
            f"{name}的{msg}。建议尽快咨询医生，"
            "并注意日常监测。需要我提供更详细的建议吗？"
        )

    def _analyze_reports(self, name: str, reports: list[dict]) -> str:
        completed = [r for r in reports if r.get("ocr_status") == "completed"]
        if completed:
            r = completed[0]
            extracted = r.get("extracted_indicators", [])
            return (
                f"{name}的{r.get('type', '检查')}报告已解读，"
                f"提取到{len(extracted)}项指标。"
                + ("建议关注异常指标。" if any(
                    i.get("status") != "normal" for i in extracted
                ) else "各项指标看起来正常。")
            )
        return f"{name}有{len(reports)}份报告待解读，OCR处理完成后我会第一时间分析。"

    def _analyze_trends(self, name: str, indicators: list[dict]) -> str:
        if not indicators:
            return f"{name}暂无足够的数据进行趋势分析。"

        # Group by key
        by_key = {}
        for ind in indicators:
            key = ind.get("indicator_key")
            if key:
                by_key.setdefault(key, []).append(ind)

        if not by_key:
            return f"{name}的数据格式不支持趋势分析。"

        # Find key with most data points
        key, items = max(by_key.items(), key=lambda x: len(x[1]))
        if len(items) < 2:
            return f"{name}的指标记录还不够多，建议持续记录以便分析趋势。"

        latest = items[0]
        prev = items[1]
        trend = IndicatorEngine.evaluate_trend(
            float(latest.get("value", 0)),
            float(prev.get("value", 0)),
            key,
        )

        direction_map = {
            "up": "上升",
            "down": "下降",
            "stable": "平稳",
        }
        evaluation_map = {
            "improving": "改善",
            "worsening": "恶化",
            "stable": "保持稳定",
        }

        return (
            f"{name}的{latest.get('indicator_name', '指标')}"
            f"最近呈{direction_map.get(trend['direction'], '波动')}趋势，"
            f"整体{evaluation_map.get(trend['evaluation'], '变化不大')}。"
            f"（从{prev.get('value')}到{latest.get('value')} {latest.get('unit')}）"
        )

    def _give_advice(self, member: Member, indicators: Optional[list[dict]]) -> str:
        advice = [f"针对{member.name}的情况，建议："]
        if member.type == "child":
            advice.append("1. 保证充足睡眠，每天9-11小时")
            advice.append("2. 均衡饮食，多吃蔬菜水果")
        elif member.type == "elderly":
            advice.append("1. 定期监测血压、血糖")
            advice.append("2. 适度运动，如散步、太极")
            advice.append("3. 按时服药，定期复诊")
        else:
            advice.append("1. 每周至少150分钟中等强度运动")
            advice.append("2. 控制盐分摄入，每日不超过6克")
            advice.append("3. 定期体检，关注血压和血脂")

        if indicators:
            abnormal = [i for i in indicators if i.get("status") in ("high", "critical")]
            if any(i.get("indicator_key") == "systolic_bp" for i in abnormal):
                advice.append("4. 血压偏高，建议低盐饮食，避免情绪激动")
            if any(i.get("indicator_key") == "fasting_glucose" for i in abnormal):
                advice.append("4. 血糖偏高，建议控制糖分摄入，规律进餐")

        return "\n".join(advice)

    async def generate_family_summary(
        self,
        member_cards: list[dict],
    ) -> str:
        """Generate AI daily summary for family dashboard."""
        if self.api_key:
            return f"[AI] 家庭健康概览：共{len(member_cards)}位成员，已生成智能摘要。"

        total_abnormal = sum(c.get("abnormal_count", 0) for c in member_cards)
        critical_members = [c for c in member_cards if c.get("latest_status") == "critical"]
        high_members = [c for c in member_cards if c.get("latest_status") in ("high", "low")]

        if critical_members:
            names = "、".join(c["name"] for c in critical_members)
            reply = f"⚠️ 今日重点关注：{names}有关键指标严重异常，建议尽快就医复查。"
        elif high_members:
            names = "、".join(c["name"] for c in high_members)
            reply = f"⚡ 注意：{names}有指标偏高/偏低，建议持续关注并调整生活习惯。"
        elif total_abnormal > 0:
            reply = f"📋 今日家庭健康概览：检测到{total_abnormal}项异常指标，建议定期复查。"
        else:
            reply = "✅ 今日家庭成员指标整体平稳，继续保持良好的健康习惯！"

        return self._append_disclaimer(reply)

    def _build_context(self, member, indicators, reports) -> str:
        parts = [f"成员：{member.name}，类型：{member.type}"]
        if indicators:
            parts.append(f"最近指标：{len(indicators)}条")
        if reports:
            parts.append(f"最近报告：{len(reports)}份")
        return "，".join(parts)
