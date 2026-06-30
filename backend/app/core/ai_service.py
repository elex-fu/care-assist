from __future__ import annotations

import asyncio
import json
import re

from app.ai.factory import get_default_provider
from app.ai.provider import AIProvider
from app.config import settings
from app.core.indicator_engine import IndicatorEngine
from app.core.logging import get_logger
from app.models.member import Member
from app.models.report import Report

logger = get_logger(__name__)


class AIService:
    """AI health assistant service.

    In production, calls are routed to the configured AI provider (e.g. kimi-code).
    If the provider is unavailable or unconfigured, falls back to rule-based mock
    responses for local development and testing.
    """

    SYSTEM_PROMPT = """你是一位家庭智能健康助手，擅长解读健康指标和医疗报告。
请用简洁、温暖的中文回答，给出具体、可操作的建议。
如果指标异常，请提醒用户关注并建议就医。

免责声明：本助手的建议仅供参考，不能替代专业医生的诊断和治疗。如有严重不适，请及时就医。"""

    def __init__(self, provider: AIProvider | None = None):
        self.provider = provider

    def _get_provider(self) -> AIProvider | None:
        if self.provider is not None:
            return self.provider
        try:
            # Skip provider if API key is not configured to avoid runtime errors
            # in development environments.
            if settings.KIMI_CODE_API_KEY:
                return get_default_provider()
        except Exception:
            pass
        return None

    async def generate_reply(
        self,
        member: Member,
        conversation_history: list[dict],
        user_message: str,
        page_context: str | None = None,
        recent_indicators: list[dict] | None = None,
        recent_reports: list[dict] | None = None,
    ) -> str:
        """Generate AI reply based on member health data and user message."""
        provider = self._get_provider()
        if provider is not None:
            return await self._call_provider(
                provider,
                member,
                conversation_history,
                user_message,
                page_context,
                recent_indicators,
                recent_reports,
            )

        # Fallback to rule-based mock responses when no provider is configured
        return await self._generate_mock_reply(
            member, user_message, page_context, recent_indicators, recent_reports
        )

    async def generate_reply_stream(
        self,
        member: Member,
        conversation_history: list[dict],
        user_message: str,
        page_context: str | None = None,
        recent_indicators: list[dict] | None = None,
        recent_reports: list[dict] | None = None,
    ):
        """Generate AI reply as an async generator of text chunks."""
        import asyncio

        # Get full reply first
        full_reply = await self.generate_reply(
            member, conversation_history, user_message,
            page_context, recent_indicators, recent_reports,
        )

        # Stream by sentences for a natural typing effect
        sentences = re.split(r'(?<=[。！？\n])', full_reply)
        sentences = [s for s in sentences if s]

        for sentence in sentences:
            yield sentence
            await asyncio.sleep(0.15)  # Simulate typing delay

    async def _call_provider(
        self,
        provider: AIProvider,
        member: Member,
        history: list[dict],
        message: str,
        page_context: str | None,
        indicators: list[dict] | None,
        reports: list[dict] | None,
    ) -> str:
        """Call the configured AI provider with built context."""
        context = self._build_context(member, indicators, reports)
        system_prompt = self.SYSTEM_PROMPT
        if page_context:
            system_prompt += f"\n当前页面上下文：{page_context}"

        messages = [{"role": "system", "content": system_prompt}]
        # Include last 10 messages of history to stay within context limits
        for msg in (history or [])[-10:]:
            role = msg.get("role")
            content = msg.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": f"{context}\n用户问题：{message}"})

        reply = await provider.chat(messages, stream=False, max_tokens=1024, temperature=0.7)
        return self._append_disclaimer(reply)

    def _append_disclaimer(self, reply: str) -> str:
        disclaimer = "\n\n【免责声明】本助手的建议仅供参考，不能替代专业医生的诊断和治疗。如有严重不适，请及时就医。"
        if disclaimer not in reply:
            reply += disclaimer
        return reply

    async def _generate_mock_reply(
        self,
        member: Member,
        user_message: str,
        page_context: str | None,
        recent_indicators: list[dict] | None,
        recent_reports: list[dict] | None,
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

    def _give_advice(self, member: Member, indicators: list[dict] | None) -> str:
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

    QUICK_QUESTION_TEMPLATES = {
        "pages/home/home": ["{name}最近指标怎么样？", "今天需要关注哪些健康提醒？"],
        "pages/indicators/indicators": ["{name}的血压趋势如何？", "哪些指标需要特别关注？"],
        "pages/reports/reports": ["帮我解读{name}最新报告", "报告中有哪些异常指标？"],
        "pages/medication/medication": ["{name}今天吃药了吗？", "最近漏服过药吗？"],
        "pages/vaccine/vaccine": ["{name}下一针疫苗什么时候打？", "有没有逾期的疫苗？"],
    }

    async def generate_quick_questions(
        self,
        member: Member,
        page_context: str | None = None,
        recent_indicators: list[dict] | None = None,
        recent_reports: list[dict] | None = None,
    ) -> list[str]:
        """Generate contextual quick question suggestions for the AI page."""
        provider = self._get_provider()
        if provider is not None:
            try:
                prompt = self._build_quick_questions_prompt(
                    member, page_context, recent_indicators, recent_reports
                )
                reply = await provider.chat(
                    [{"role": "user", "content": prompt}],
                    stream=False,
                    max_tokens=256,
                    temperature=0.7,
                )
                questions = [q.strip("-\n ") for q in reply.split("\n") if q.strip()]
                return questions[:4]
            except Exception:
                pass
        return self._rule_based_quick_questions(
            member, page_context, recent_indicators, recent_reports
        )

    def _build_quick_questions_prompt(
        self,
        member: Member,
        page_context: str | None,
        recent_indicators: list[dict] | None,
        recent_reports: list[dict] | None,
    ) -> str:
        lines = [
            f"请为家庭健康助手生成 2-4 条用户可能想问的快捷问题，针对成员 {member.name}。",
            f"当前页面：{page_context or '首页'}",
        ]
        if recent_indicators:
            lines.append(f"最近指标：{len(recent_indicators)} 条")
        if recent_reports:
            lines.append(f"最近报告：{len(recent_reports)} 份")
        lines.append("请只输出问题列表，每行一条，简洁自然。")
        return "\n".join(lines)

    def _rule_based_quick_questions(
        self,
        member: Member,
        page_context: str | None,
        recent_indicators: list[dict] | None,
        recent_reports: list[dict] | None,
    ) -> list[str]:
        base = list(self.QUICK_QUESTION_TEMPLATES.get(page_context or "", ["{name}最近身体怎么样？"]))
        if recent_indicators:
            base.append("{name}最近指标有什么变化？")
        if recent_reports:
            base.append("帮我总结{name}最近的检查报告")
        return [q.format(name=member.name) for q in base[:4]]

    async def summarize_report(
        self,
        member: Member,
        report: Report,
    ) -> str:
        """Generate an AI summary for a report and store it on the report."""
        extracted = report.extracted_indicators or []
        provider = self._get_provider()
        if provider is not None:
            try:
                prompt = self._build_report_summary_prompt(member, report, extracted)
                reply = await provider.chat(
                    [{"role": "user", "content": prompt}],
                    stream=False,
                    max_tokens=512,
                    temperature=0.5,
                )
                return self._append_disclaimer(reply)
            except Exception:
                pass
        return self._rule_based_summary(member, report, extracted)

    STRUCTURED_SYSTEM_PROMPT = """你是一位家庭智能健康助手。请根据用户问题和提供的健康数据，
按以下 JSON 格式输出回答。只输出 JSON，不要添加任何解释或 Markdown 代码块。

{
  "answer": "直接、温暖的中文回答（不超过150字）",
  "data_cards": [
    {"title": "指标/数据名称", "value": "数值+单位", "status": "normal|high|low|critical"}
  ],
  "suggestions": ["具体可操作的健康建议1", "建议2"],
  "follow_up_questions": ["引导用户进一步描述的追问1", "追问2"],
  "disclaimer": "本建议仅供参考，不能替代专业医生诊断和治疗。"
}

如果问题与健康无关，data_cards 和 suggestions 可为空数组。"""

    def _build_report_summary_prompt(
        self,
        member: Member,
        report: Report,
        extracted: list[dict],
    ) -> str:
        lines = [f"请用简洁中文总结{member.name}的{report.type}报告："]
        for item in extracted[:20]:
            lines.append(
                f"- {item.get('indicator_name')}: {item.get('value')} {item.get('unit')}"
            )
        return "\n".join(lines)

    async def generate_structured_reply(
        self,
        member: Member,
        conversation_history: list[dict],
        user_message: str,
        page_context: str | None = None,
        recent_indicators: list[dict] | None = None,
        recent_reports: list[dict] | None = None,
    ) -> dict:
        """Generate a 5-layer structured AI reply."""
        provider = self._get_provider()
        if provider is not None:
            try:
                context = self._build_context(member, recent_indicators, recent_reports)
                messages = [
                    {"role": "system", "content": self.STRUCTURED_SYSTEM_PROMPT},
                ]
                if conversation_history:
                    messages.extend(conversation_history[-6:])
                messages.append({"role": "user", "content": f"{context}\n\n用户问题：{user_message}"})

                reply = await provider.chat(
                    messages,
                    stream=False,
                    max_tokens=1024,
                    temperature=1.0,
                )
                parsed = self._parse_structured_json(reply)
                if parsed:
                    return parsed
            except Exception as exc:
                logger.warning(f"Structured AI reply failed: {exc}")

        return self._rule_based_structured_reply(member, user_message, recent_indicators)

    def _parse_structured_json(self, text: str) -> dict | None:
        """Extract and validate structured JSON from model output."""
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```json", 1)[-1].split("```", 1)[0].strip()
        try:
            parsed = json.loads(text)
            required = {"answer", "data_cards", "suggestions", "follow_up_questions", "disclaimer"}
            if not required.issubset(parsed.keys()):
                return None
            return {
                "answer": str(parsed.get("answer", "")),
                "data_cards": parsed.get("data_cards", []),
                "suggestions": parsed.get("suggestions", []),
                "follow_up_questions": parsed.get("follow_up_questions", []),
                "disclaimer": str(parsed.get("disclaimer", "")),
            }
        except Exception:
            return None

    def _rule_based_structured_reply(
        self,
        member: Member,
        user_message: str,
        recent_indicators: list[dict] | None,
    ) -> dict:
        """Fallback structured reply when AI provider is unavailable."""
        data_cards = []
        if recent_indicators:
            for i in recent_indicators[:3]:
                data_cards.append({
                    "title": i.get("indicator_name", i.get("indicator_key", "指标")),
                    "value": f"{i.get('value', '')} {i.get('unit', '')}".strip(),
                    "status": i.get("status", "unknown"),
                })
        return {
            "answer": f"{member.name}您好，我已收到您的问题。当前可提供最近指标供您参考，具体诊断建议咨询医生。",
            "data_cards": data_cards,
            "suggestions": ["保持健康作息", "定期监测指标", "如有不适及时就医"],
            "follow_up_questions": ["您最近有哪里不舒服吗？", "需要我帮您分析哪项指标？"],
            "disclaimer": "本建议仅供参考，不能替代专业医生诊断和治疗。",
        }

    def _rule_based_summary(
        self,
        member: Member,
        report: Report,
        extracted: list[dict],
    ) -> str:
        if not extracted:
            return f"{member.name}的{report.type}报告暂未识别到指标，请检查图片清晰度。"
        abnormal = [i for i in extracted if i.get("status") in ("low", "high", "critical")]
        if abnormal:
            names = "、".join(i["indicator_name"] for i in abnormal[:5])
            return f"{member.name}的报告中{names}等{len(abnormal)}项指标异常，建议进一步复查。"
        return f"{member.name}的报告中各项指标均在参考范围内，整体情况平稳。"

    async def generate_family_summary(
        self,
        member_cards: list[dict],
        timeout: float = 5.0,
    ) -> str:
        """Generate AI daily summary for family dashboard."""
        provider = self._get_provider()
        if provider is not None:
            try:
                reply = await asyncio.wait_for(
                    provider.generate_summary({"member_cards": member_cards}),
                    timeout=timeout,
                )
                return self._append_disclaimer(reply)
            except TimeoutError:
                # Dashboard should not block on slow AI provider; fall back quickly.
                pass
            except Exception:
                # Fall back to rule-based summary on provider failure.
                pass

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
