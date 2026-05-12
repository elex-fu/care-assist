# 家庭智能健康助手 — 后端项目设计

> 版本：v1.0 | 日期：2026-05-08 | 读者：后端开发工程师 | 状态：设计定稿

---

## 目录

1. [项目结构](#一项目结构)
2. [FastAPI 主应用配置](#二fastapi-主应用配置)
3. [依赖注入设计](#三依赖注入设计)
4. [WebSocket 管理器](#四websocket-管理器)
5. [Service 业务逻辑层](#五service-业务逻辑层)
6. [AI Provider 抽象层](#六ai-provider-抽象层)
7. [OCR 与报告解析流程](#七ocr-与报告解析流程)
8. [异常判断引擎](#八异常判断引擎)
9. [AI 对话上下文管理](#九ai-对话上下文管理)
10. [提醒系统](#十提醒系统)
11. [家庭成员共享](#十一家庭成员共享)
12. [数据导出](#十二数据导出)
13. [自动清理任务](#十三自动清理任务)

---

## 一、项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI应用入口，注册路由/中间件/异常处理
│   ├── config.py                # Pydantic Settings 配置管理
│   ├── dependencies.py          # 依赖注入（DB会话、Redis、当前用户）
│   ├── middlewares/
│   │   ├── auth.py              # JWT鉴权中间件
│   │   ├── rate_limit.py        # 限流中间件
│   │   └── logging.py           # 请求日志中间件
│   ├── routers/                 # HTTP API路由（按模块组织）
│   │   ├── members.py           # 成员管理
│   │   ├── indicators.py        # 指标CRUD
│   │   ├── reports.py           # 报告上传/OCR/确认
│   │   ├── hospitals.py         # 住院管理
│   │   ├── ai.py                # AI对话/快捷问题
│   │   ├── reminders.py         # 提醒管理
│   │   ├── child.py             # 儿童疫苗/成长
│   │   └── export.py            # 数据导出
│   ├── services/                # 业务逻辑层
│   │   ├── member_service.py
│   │   ├── indicator_service.py
│   │   ├── report_service.py
│   │   ├── hospital_service.py
│   │   ├── ai_service.py
│   │   ├── reminder_service.py
│   │   └── child_service.py
│   ├── models/                  # SQLAlchemy ORM模型
│   │   ├── member.py
│   │   ├── indicator.py
│   │   ├── report.py
│   │   ├── hospital.py
│   │   ├── reminder.py
│   │   └── ai_conversation.py
│   ├── schemas/                 # Pydantic 请求/响应模型
│   │   ├── member.py
│   │   ├── indicator.py
│   │   └── common.py
│   ├── ai/
│   │   ├── provider.py          # AIProvider ABC抽象接口
│   │   ├── kimi_provider.py
│   │   ├── deepseek_provider.py
│   │   ├── openai_provider.py
│   │   ├── qwen_provider.py
│   │   └── factory.py           # ProviderFactory + 故障降级
│   ├── core/
│   │   ├── exceptions.py        # 自定义业务异常
│   │   ├── security.py          # JWT/密码/加密工具
│   │   └── indicator_engine.py  # 异常判断/趋势计算引擎
│   ├── db/
│   │   ├── session.py           # SQLAlchemy async session
│   │   └── base.py              # Base模型/通用查询
│   └── tasks/
│       ├── celery_app.py        # Celery应用配置
│       ├── ocr_task.py          # OCR异步任务
│       ├── analyze_task.py      # 报告AI解读任务
│       ├── reminder_task.py     # 定时提醒任务
│       └── cleanup_task.py      # 数据自动清理任务
├── alembic/                     # 数据库迁移
├── tests/
├── Dockerfile
├── docker-compose.yml
```

### 数据库连接池配置

```python
# app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import aioredis

DATABASE_URL = "mysql+aiomysql://user:pass@host/db"

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,           # 常驻连接数
    max_overflow=10,        # 高峰期可额外创建的连接
    pool_pre_ping=True,     # 连接前发送 ping，自动回收死连接
    pool_recycle=3600,      # 连接 1 小时后强制回收，防止 MySQL wait_timeout 断开
    echo=False,
)

async_session = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Redis 连接池（WebSocket 状态共享 + 限流计数器）
redis_pool = aioredis.ConnectionPool.from_url(
    "redis://localhost:6379", max_connections=50
)
```
├── requirements.txt
└── pyproject.toml
```

---

## 二、FastAPI 主应用配置

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import members, indicators, reports, hospitals, ai, reminders, child, export
from app.middlewares import auth, rate_limit, logging
from app.config import settings

app = FastAPI(
    title="家庭智能健康助手 API",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None
)

# 中间件（顺序很重要）
app.add_middleware(logging.RequestLoggingMiddleware)
app.add_middleware(rate_limit.RateLimitMiddleware)
app.add_middleware(auth.JWTAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://servicewechat.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 路由注册
app.include_router(members.router, prefix="/api/members", tags=["成员"])
app.include_router(indicators.router, prefix="/api/indicators", tags=["指标"])
app.include_router(reports.router, prefix="/api/reports", tags=["报告"])
app.include_router(hospitals.router, prefix="/api/hospitals", tags=["住院"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(reminders.router, prefix="/api/reminders", tags=["提醒"])
app.include_router(child.router, prefix="/api/child", tags=["儿童"])
app.include_router(export.router, prefix="/api/export", tags=["导出"])

# WebSocket路由
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await ws_manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
```

---

## 三、依赖注入设计

```python
# app/dependencies.py
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session
from app.core.security import decode_jwt
from app.models.member import Member

async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session

async def get_current_member(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db)
) -> Member:
    token = authorization.replace("Bearer ", "")
    payload = decode_jwt(token)
    member = await db.get(Member, payload["sub"])
    if not member:
        raise HTTPException(status_code=401, detail="用户不存在")
    return member

async def get_redis():
    # aioredis 连接池
    from app.db.session import redis_pool
    async with redis_pool as redis:
        yield redis
```

---

## 四、WebSocket 管理器

```python
# app/services/ws_manager.py
from fastapi import WebSocket
from typing import Dict, List
import json

class ConnectionStore:
    """连接存储抽象：生产环境用Redis，单实例开发可回退到内存Dict"""
    async def add(self, member_id: str, websocket_id: str) -> None: ...
    async def remove(self, member_id: str, websocket_id: str) -> None: ...
    async def get_connections(self, member_id: str) -> List[str]: ...

class RedisConnectionStore(ConnectionStore):
    def __init__(self, redis):
        self.redis = redis
        self.key_prefix = "ws:connections"

    async def add(self, member_id: str, websocket_id: str) -> None:
        await self.redis.sadd(f"{self.key_prefix}:{member_id}", websocket_id)

    async def remove(self, member_id: str, websocket_id: str) -> None:
        await self.redis.srem(f"{self.key_prefix}:{member_id}", websocket_id)

    async def get_connections(self, member_id: str) -> List[str]:
        return [x.decode() for x in await self.redis.smembers(f"{self.key_prefix}:{member_id}")]

class ConnectionManager:
    def __init__(self, store: ConnectionStore):
        self.store = store
        self._ws_registry: Dict[str, WebSocket] = {}  # 仅本实例持有的WebSocket对象

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        member_id = self._extract_member_id(websocket)
        ws_id = str(id(websocket))
        self._ws_registry[ws_id] = websocket
        await self.store.add(member_id, ws_id)

    async def disconnect(self, websocket: WebSocket):
        member_id = self._extract_member_id(websocket)
        ws_id = str(id(websocket))
        self._ws_registry.pop(ws_id, None)
        await self.store.remove(member_id, ws_id)

    async def send_to_member(self, member_id: str, message: dict):
        ws_ids = await self.store.get_connections(member_id)
        for ws_id in ws_ids:
            ws = self._ws_registry.get(ws_id)
            if ws:
                await ws.send_json(message)

    async def handle_message(self, websocket: WebSocket, data: dict):
        # 速率限制：单连接每秒最多10条消息
        if not self._check_rate_limit(websocket):
            await websocket.close(code=1008, reason="rate limit exceeded")
            return
        msg_type = data.get("type")
        if msg_type == "ping":
            await websocket.send_json({"type": "pong"})
        elif msg_type == "chat":
            await ai_service.handle_chat_stream(websocket, data)

    def _check_rate_limit(self, websocket: WebSocket) -> bool:
        # 实现略：基于Redis的滑动窗口计数器
        return True

ws_manager = ConnectionManager(store=RedisConnectionStore(redis_pool))
```

---

## 五、Service 业务逻辑层

### 5.1 HospitalService — 住院快捷对比

```python
# app/services/hospital_service.py

class HospitalService:
    async def get_yesterday_comparison(self, hospital_id: str, member_id: str):
        """今日vs昨日快捷对比API"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # 获取两天的所有指标
        today_indicators = await self.get_indicators_by_date(hospital_id, today)
        yesterday_indicators = await self.get_indicators_by_date(hospital_id, yesterday)

        # 自动计算变化
        comparison = []
        for key in set(today_indicators.keys()) & set(yesterday_indicators.keys()):
            today_val = today_indicators[key]
            yesterday_val = yesterday_indicators[key]
            change = today_val - yesterday_val
            change_pct = (change / yesterday_val * 100) if yesterday_val else 0

            evaluation = self._evaluate_change(key, change, today_val)
            comparison.append({
                "indicator_key": key,
                "indicator_name": INDICATOR_NAMES.get(key, key),
                "today": today_val,
                "yesterday": yesterday_val,
                "change": round(change, 2),
                "change_percent": round(change_pct, 1),
                "evaluation": evaluation,  # improving / worsening / stable / concerning
                "unit": INDICATOR_UNITS.get(key, "")
            })

        # 排序：异常项优先，变化大的优先
        comparison.sort(key=lambda x: (
            0 if x["evaluation"] in ["worsening", "concerning"] else 1,
            abs(x["change_percent"])
        ), reverse=True)

        return {
            "hospital_id": hospital_id,
            "today": today.isoformat(),
            "yesterday": yesterday.isoformat(),
            "total": len(comparison),
            "improved": sum(1 for c in comparison if c["evaluation"] == "improving"),
            "worsened": sum(1 for c in comparison if c["evaluation"] in ["worsening", "concerning"]),
            "stable": sum(1 for c in comparison if c["evaluation"] == "stable"),
            "indicators": comparison
        }

    async def get_indicators_by_date(self, hospital_id: str, target_date: date):
        """获取某天住院的所有指标"""
        # 查询该住院事件下、该日期的所有检查批次指标
        query = select(IndicatorData).where(
            IndicatorData.hospital_id == hospital_id,
            IndicatorData.record_date == target_date
        )
        result = await db.execute(query)
        return {row.indicator_key: row.value for row in result.scalars()}
```

### 5.2 ChildService — 按龄动态推荐

```python
# app/services/child_service.py

class ChildService:
    AGE_BASED_LAYOUTS = {
        # 0-3个月
        (0, 3): {
            "todo_items": ["vaccine_hepb_2", "checkup_1m"],
            "growth_focus": ["height", "weight", "head_circumference"],
            "quick_links": ["growth", "vaccine", "ai"],
            "ai_suggestions": ["母乳还是配方奶？", "每天睡多久合适？", "黄疸正常吗？"]
        },
        # 3-6个月
        (3, 6): {
            "todo_items": ["vaccine_dtp_1", "checkup_3m"],
            "growth_focus": ["height", "weight", "head_circumference"],
            "quick_links": ["growth", "vaccine", "milestone", "ai"],
            "ai_suggestions": ["辅食什么时候加？", "翻身正常吗？", "体重增长够吗？"]
        },
        # 6-12个月
        (6, 12): {
            "todo_items": ["vaccine_hepb_3", "vaccine_mmr_1", "checkup_6m", "checkup_8m"],
            "growth_focus": ["height", "weight", "bmi"],
            "quick_links": ["growth", "vaccine", "milestone", "nutrition", "ai"],
            "ai_suggestions": ["辅食怎么吃？", "缺钙的表现？", "出牙要注意什么？"]
        },
        # 1-3岁
        (12, 36): {
            "todo_items": ["vaccine_varicella", "checkup_1y", "checkup_2y"],
            "growth_focus": ["height", "weight", "bmi"],
            "quick_links": ["growth", "vaccine", "milestone", "nutrition", "ai"],
            "ai_suggestions": ["说话晚正常吗？", "挑食怎么办？", "每天户外多久？"]
        },
        # 3-6岁
        (36, 72): {
            "todo_items": ["vaccine_dtp_4", "checkup_3y", "checkup_4y", "checkup_5y"],
            "growth_focus": ["height", "weight", "bmi", "vision"],
            "quick_links": ["growth", "vaccine", "milestone", "vision", "teeth", "ai"],
            "ai_suggestions": ["视力怎么保护？", "牙齿涂氟？", "准备上幼儿园？"]
        }
    }

    async def get_dashboard(self, member_id: str):
        """获取儿童看板（按龄动态）"""
        member = await MemberService.get(member_id)
        age_months = member.age_months

        # 找到对应的年龄段布局
        layout = None
        for (min_age, max_age), config in self.AGE_BASED_LAYOUTS.items():
            if min_age <= age_months <= max_age:
                layout = config
                break

        if not layout:
            layout = self.AGE_BASED_LAYOUTS[(36, 72)]  # 默认3-6岁

        # 生成待办清单
        todos = []
        for item_key in layout["todo_items"]:
            item = await self._get_todo_item(member_id, item_key, age_months)
            if item:
                todos.append(item)

        # 生成正面反馈
        positives = await self._get_positive_feedback(member_id, age_months)

        # 快捷入口
        quick_links = await self._get_quick_links(member_id, layout["quick_links"])

        return {
            "member_id": member_id,
            "age_months": age_months,
            "age_display": self._format_age(age_months),
            "todos": todos,
            "positives": positives,
            "quick_links": quick_links,
            "ai_suggestions": layout["ai_suggestions"]
        }
```

---

## 六、AI Provider 抽象层

### 6.1 抽象接口

```python
# app/ai/provider.py
from abc import ABC, abstractmethod
from typing import AsyncIterator, Union

class AIProvider(ABC):
    """AI Provider 抽象接口，所有Provider必须实现此接口"""

    @abstractmethod
    async def chat(self, messages: list, stream: bool = False) -> Union[AsyncIterator[str], str]:
        """通用对话接口
        Args:
            messages: OpenAI格式消息列表 [{role, content}]
            stream: 是否流式返回
        Returns:
            stream=True: AsyncIterator[str] 逐字返回
            stream=False: str 完整返回
        """
        pass

    @abstractmethod
    async def analyze_image(self, image_url: str, prompt: str) -> str:
        """图片分析接口（报告OCR/指标提取）
        Args:
            image_url: 图片可访问URL
            prompt: 分析提示词
        Returns:
            JSON格式字符串，包含提取的结构化指标
        """
        pass

    @abstractmethod
    async def generate_summary(self, context: dict) -> str:
        """生成就诊摘要/病情简报
        Args:
            context: 包含成员信息、指标列表、异常项的字典
        Returns:
            Markdown格式摘要文本
        """
        pass
```

### 6.2 Kimi Provider 实现

```python
# app/ai/kimi_provider.py
import httpx
from app.ai.provider import AIProvider
from app.config import settings

class KimiProvider(AIProvider):
    def __init__(self):
        self.api_key = settings.KIMI_API_KEY
        self.base_url = "https://api.moonshot.cn/v1"
        self.client = httpx.AsyncClient(timeout=60.0)

    async def chat(self, messages: list, stream: bool = False):
        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": "moonshot-v1-128k",
                "messages": messages,
                "stream": stream
            }
        )
        if stream:
            # 解析SSE流
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunk = line[6:]
                    if chunk == "[DONE]": break
                    yield json.loads(chunk)["choices"][0]["delta"].get("content", "")
        else:
            return response.json()["choices"][0]["message"]["content"]

    async def analyze_image(self, image_url: str, prompt: str) -> str:
        messages = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": prompt}
            ]
        }]
        return await self.chat(messages, stream=False)

    async def generate_summary(self, context: dict) -> str:
        prompt = self._build_summary_prompt(context)
        return await self.chat([{"role": "user", "content": prompt}], stream=False)
```

### 6.3 Provider 工厂与故障降级

```python
# app/ai/factory.py
from app.ai.provider import AIProvider
from app.ai.kimi_provider import KimiProvider
from app.ai.deepseek_provider import DeepSeekProvider
from app.ai.openai_provider import OpenAIProvider
from app.config import settings

class ProviderFactory:
    _providers = {
        "kimi": KimiProvider,
        "deepseek": DeepSeekProvider,
        "openai": OpenAIProvider,
        "qwen": QwenProvider,
    }

    @classmethod
    def get_provider(cls, name: str = None) -> AIProvider:
        name = name or settings.DEFAULT_AI_PROVIDER
        provider_cls = cls._providers.get(name)
        if not provider_cls:
            raise ValueError(f"Unknown provider: {name}")
        return provider_cls()

    @classmethod
    async def chat_with_fallback(cls, messages: list, stream: bool = False):
        """带故障降级的对话调用"""
        providers = [settings.DEFAULT_AI_PROVIDER] + settings.FALLBACK_PROVIDERS
        for provider_name in providers:
            try:
                provider = cls.get_provider(provider_name)
                return await provider.chat(messages, stream)
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                continue
        raise RuntimeError("All AI providers failed")
```

---

## 七、OCR 与报告解析流程

```
用户拍照上传
    ↓
微信小程序 wx.chooseImage + wx.uploadFile
    ↓
后端 /api/reports/upload 接收图片
    ↓
后端签名直传 → 对象存储（MinIO/OSS）
    ↓
返回 report_id + image_url
    ↓
前端显示 "AI正在读报告..." 进度条
    ↓
后端提交 Celery 异步任务 ocr_task
    ↓
Celery Worker 执行：
    1. 从OSS获取图片URL
    2. 调用 AIProvider.analyze_image()
    3. Prompt 工程："请提取这份体检报告中的所有检验指标，返回JSON格式：
       [{name, value, unit, reference_range}]"
    4. AI返回结构化JSON
    5. 指标标准化映射（名称/单位归一化）
    6. 异常判断引擎计算状态
    7. 写入数据库（reports + indicators）
    8. 生成 health_events 时间轴记录
    9. WebSocket推送 "ocr_complete" 给前端
    ↓
前端收到推送 → 自动刷新 → 显示结果页
```

```python
# app/tasks/ocr_task.py
from celery import shared_task
from app.ai.factory import ProviderFactory
from app.core.indicator_engine import IndicatorEngine
from app.services.report_service import ReportService

from asgiref.sync import async_to_sync

@shared_task(bind=True, max_retries=3)
def ocr_and_analyze_report(self, report_id: str, image_url: str, member_id: str):
    """Celery 同步任务包装器：内部调用 async 逻辑"""
    return async_to_sync(_ocr_async)(report_id, image_url, member_id)

async def _ocr_async(report_id: str, image_url: str, member_id: str):
    try:
        # 1. 调用AI多模态解析
        provider = ProviderFactory.get_provider("kimi")  # OCR用Kimi视觉能力强
        prompt = """请仔细识别这份医疗检验报告，提取所有检验指标。
要求：
1. 返回标准JSON数组，每个指标包含：name（指标名称）、value（数值）、unit（单位）、reference_range（参考范围，如"3.9-6.1"）
2. 如果值是范围（如"120-140"），取平均值
3. 忽略非数值项（如"阴性"可保留但标记为text_type）
4. 单位要标准化（如"mmol/l"统一为"mmol/L"）"""

        result = provider.analyze_image(image_url, prompt)
        extracted = json.loads(result)

        # 2. 指标标准化
        normalized = []
        for item in extracted:
            std = IndicatorEngine.standardize(item["name"], item["unit"])
            status = IndicatorEngine.judge(
                value=item["value"],
                indicator_key=std["key"],
                age_months=member.age_months
            )
            normalized.append({
                **item,
                "indicator_key": std["key"],
                "indicator_name": std["display_name"],
                "unit": std["unit"],
                "status": status
            })

        # 3. 数据库事务写入（reports + indicator_data + health_events 三表一致）
        from app.db.session import async_session
        from app.models.indicator import IndicatorData
        from app.models.health_event import HealthEvent

        async with async_session.begin() as session:
            # 3.1 更新报告状态
            report = await session.get(Report, report_id)
            report.ocr_status = "completed"
            report.extracted_indicators = normalized

            # 3.2 写入指标数据
            indicator_records = []
            for item in normalized:
                deviation = IndicatorEngine.calculate_deviation(
                    value=item["value"],
                    indicator_key=item["indicator_key"],
                    age_months=member.age_months
                )
                indicator = IndicatorData(
                    member_id=member_id,
                    indicator_key=item["indicator_key"],
                    indicator_name=item["indicator_name"],
                    value=item["value"],
                    unit=item["unit"],
                    lower_limit=item.get("lower_limit"),
                    upper_limit=item.get("upper_limit"),
                    status=item["status"],
                    deviation_percent=round(deviation * 100, 2),
                    record_date=date.today(),
                    source_report_id=report_id
                )
                session.add(indicator)
                indicator_records.append(indicator)

            # 3.3 生成时间轴事件
            abnormal_count = sum(1 for i in normalized if i["status"] != "normal")
            event = HealthEvent(
                member_id=member_id,
                type="lab",
                event_date=date.today(),
                report_id=report_id,
                status="abnormal" if abnormal_count > 0 else "normal",
                abnormal_count=abnormal_count
            )
            session.add(event)
            # 事务提交：三表同时成功或同时回滚

        # 4. 推送完成通知
        ws_manager.send_to_member(member_id, {
            "type": "ocr_complete",
            "report_id": report_id,
            "indicator_count": len(normalized),
            "abnormal_count": abnormal_count
        })

    except Exception as exc:
        # 重试3次后标记失败
        if self.request.retries < 3:
            raise self.retry(exc=exc, countdown=10)
        # 事务失败自动回滚，标记报告为 failed
        ReportService.mark_ocr_failed(report_id, str(exc))
```

---

## 八、异常判断引擎

```python
# app/core/indicator_engine.py
from typing import Optional
from dataclasses import dataclass

@dataclass
class Threshold:
    lower: Optional[float] = None
    upper: Optional[float] = None

class IndicatorEngine:
    # 标准指标库（名称映射 + 阈值）
    THRESHOLDS = {
        "systolic_bp": {
            "name": "收缩压", "unit": "mmHg",
            "threshold": Threshold(90, 140),
            "age_groups": [
                {"max_age": 12, "threshold": Threshold(80, 120)},
                {"max_age": 60, "threshold": Threshold(90, 140)},
                {"max_age": 999, "threshold": Threshold(90, 150)},
            ]
        },
        "hemoglobin": {
            "name": "血红蛋白", "unit": "g/L",
            "threshold": Threshold(120, 160),
            "age_groups": [
                {"max_age": 1, "threshold": Threshold(100, 140)},
                {"max_age": 12, "threshold": Threshold(110, 145)},
                {"max_age": 60, "threshold": Threshold(120, 160)},
                {"max_age": 999, "threshold": Threshold(110, 160)},
            ]
        },
        # ... 更多指标
    }

    @classmethod
    def standardize(cls, raw_name: str, raw_unit: str) -> dict:
        """指标名称和单位标准化"""
        # 模糊匹配：使用预置的同义词库 + Levenshtein距离
        name_mapping = {
            "血压（收缩压）": "systolic_bp",
            "收缩压": "systolic_bp",
            "SBP": "systolic_bp",
            # ...
        }
        key = name_mapping.get(raw_name.strip())
        if not key:
            key = f"custom_{hash(raw_name)}"
        return {
            "key": key,
            "display_name": cls.THRESHOLDS.get(key, {}).get("name", raw_name),
            "unit": cls._normalize_unit(raw_unit)
        }

    @classmethod
    def judge(cls, value: float, indicator_key: str, age_months: Optional[int] = None) -> str:
        """判断指标状态：normal / low / high / critical"""
        config = cls.THRESHOLDS.get(indicator_key)
        if not config:
            return "unknown"

        threshold = config["threshold"]

        # 按年龄段调整阈值
        if age_months and "age_groups" in config:
            for group in config["age_groups"]:
                if age_months <= group["max_age"]:
                    threshold = group["threshold"]
                    break

        lower, upper = threshold.lower, threshold.upper

        # 危急值：偏离参考范围30%以上
        if lower is not None and value < lower * 0.7:
            return "critical"
        if upper is not None and value > upper * 1.3:
            return "critical"

        # 异常值
        if lower is not None and value < lower:
            return "low"
        if upper is not None and value > upper:
            return "high"

        return "normal"

    # 前端状态映射约定（4级后端 → 3色前端）：
    # normal  → 正常
    # low     → 注意（文案显示"偏低"）
    # high    → 注意（文案显示"偏高"）
    # critical → 严重异常
    # 前端实现参考 functional_ui_design.md 2.1 状态映射表

    @classmethod
    def calculate_deviation(cls, value: float, indicator_key: str, age_months: Optional[int] = None) -> float:
        """计算指标偏离参考范围的百分比（用于后端自动判断提醒紧急程度）
        返回值：
        - 0 = 在正常范围内
        - 正数 = 高于上限的百分比（如 0.25 表示高25%）
        - 负数 = 低于下限的百分比（如 -0.15 表示低15%）
        """
        config = cls.THRESHOLDS.get(indicator_key)
        if not config:
            return 0.0

        threshold = config["threshold"]
        if age_months and "age_groups" in config:
            for group in config["age_groups"]:
                if age_months <= group["max_age"]:
                    threshold = group["threshold"]
                    break

        lower, upper = threshold.lower, threshold.upper

        if lower is not None and value < lower:
            return (value - lower) / lower  # 负数，如 -0.15
        if upper is not None and value > upper:
            return (value - upper) / upper  # 正数，如 0.25
        return 0.0

    @classmethod
    def evaluate_trend(cls, current: float, previous: float, indicator_key: str) -> dict:
        """趋势评价"""
        change = current - previous
        change_pct = abs(change / previous) if previous else 0

        direction = "stable" if change_pct < 0.05 else ("up" if change > 0 else "down")
        magnitude = "small" if change_pct < 0.1 else ("moderate" if change_pct < 0.3 else "large")

        # 结合指标特性判断好坏（如血糖越低越好，血红蛋白越高越好）
        is_lower_better = indicator_key in ["fasting_glucose", "ldl", "triglycerides"]
        if is_lower_better:
            evaluation = "improving" if direction == "down" else ("worsening" if direction == "up" else "stable")
        else:
            evaluation = "improving" if direction == "up" else ("worsening" if direction == "down" else "stable")

        return {"direction": direction, "magnitude": magnitude, "evaluation": evaluation}
```

---

## 九、AI 对话上下文管理

```python
# app/services/ai_service.py
from app.ai.factory import ProviderFactory
from app.models.ai_conversation import AIConversation
from app.core.indicator_engine import IndicatorEngine

class AIService:
    SYSTEM_PROMPT = """你是一位家庭健康顾问助手，帮助用户理解健康指标和医疗报告。
规则：
1. 用通俗易懂的中文回答，避免专业术语（如用"血里的红细胞"代替"血红蛋白"）
2. 每次回答结构：先给结论（"没事"/"建议复查"/"尽快就医"），再解释原因
3. 引用具体数据时注明日期
4. 不给出具体诊断，只提供参考建议
5. 结尾必加医疗免责声明"""

    async def handle_chat(self, member_id: str, message: str, page_context: str) -> dict:
        # 1. 获取/创建对话历史
        conversation = await self.get_or_create_conversation(member_id, page_context)

        # 2. 构建上下文（四级上下文）
        context = await self.build_context(member_id, page_context)

        # 3. 组装消息
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "system", "content": f"当前用户上下文：{context}"},
            *conversation.messages[-10:],  # 最近10轮
            {"role": "user", "content": message}
        ]

        # 4. 调用AI
        reply = await ProviderFactory.chat_with_fallback(messages, stream=False)

        # 5. 解析回复（提取数据卡片、追问推荐）
        parsed = self.parse_reply(reply)

        # 6. 保存对话
        await self.save_message(conversation.id, "user", message)
        await self.save_message(conversation.id, "ai", reply, parsed.get("data_cards"))

        return {
            "reply": parsed["text"],
            "data_cards": parsed.get("data_cards", []),
            "suggested_questions": parsed.get("suggested_questions", [])
        }

    async def build_context(self, member_id: str, page_context: str) -> str:
        """构建四级上下文：成员信息 + 页面场景 + 当前指标 + 最近异常"""
        parts = []

        # 成员上下文
        member = await MemberService.get(member_id)
        parts.append(f"成员：{member.name}，{member.age}岁，{member.gender}")

        # 页面上下文
        parts.append(f"当前页面：{page_context}")

        # 指标上下文（如果是指标相关页面）
        if page_context.startswith("indicator:"):
            indicator_name = page_context.split(":")[1]
            history = await IndicatorService.get_history(member_id, indicator_name, limit=5)
            parts.append(f"最近{indicator_name}记录：{history}")

        # 最近异常
        abnormalities = await IndicatorService.get_recent_abnormal(member_id, days=30)
        if abnormalities:
            parts.append(f"最近30天异常指标：{abnormalities}")

        return "\n".join(parts)

    async def handle_chat_stream(self, websocket, data: dict):
        """WebSocket流式对话处理"""
        member_id = data["member_id"]
        message = data["message"]
        context = await self.build_context(member_id, data.get("page_context", ""))

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "system", "content": f"上下文：{context}"},
            {"role": "user", "content": message}
        ]

        provider = ProviderFactory.get_provider()
        full_reply = ""

        async for chunk in provider.chat(messages, stream=True):
            full_reply += chunk
            await websocket.send_json({"type": "chat_chunk", "content": chunk})

        await websocket.send_json({"type": "chat_done", "content": full_reply})
```

---

## 十、提醒系统

```python
# app/services/reminder_service.py
from datetime import datetime, timedelta
from app.models.reminder import Reminder
from app.tasks.reminder_task import send_reminder_notification

class ReminderService:
    RULES = [
        {"type": "vaccine", "advance_days": 14, "repeat": "每3天", "priority": "high"},
        {"type": "vaccine_overdue", "advance_days": 0, "repeat": "每天", "priority": "critical"},
        {"type": "review", "advance_days": 7, "priority": "normal"},
        {"type": "review_urgent", "advance_days": 3, "priority": "high"},
        {"type": "checkup", "advance_days": 30, "priority": "normal"},
        {"type": "medication", "advance_days": 0, "repeat": "每天", "priority": "critical"},
    ]

    async def create_from_abnormal(self, member_id: str, indicator: dict, action: str):
        """从异常指标创建提醒（前端2级：观察/就医，后端根据偏离程度自动判断提醒时间）"""
        # 计算偏离百分比（优先使用已存储值，否则实时计算）
        deviation_pct = indicator.get('deviation_percent')
        if deviation_pct is None:
            deviation = IndicatorEngine.calculate_deviation(
                value=indicator['value'],
                indicator_key=indicator.get('indicator_key', ''),
                age_months=indicator.get('age_months')
            )
            deviation_pct = abs(round(deviation * 100, 2))

        if action == "observe":
            # 轻微异常：偏离<20%或趋势稳定
            scheduled = datetime.now() + timedelta(days=7)
            title = f"{indicator['name']}复查提醒"
            priority = "normal"
        else:  # action == "see_doctor"
            # 需关注/严重：偏离>=20%或趋势恶化
            # 后端根据实际偏离程度自动决定是3天复查还是1天就医
            if deviation_pct >= 30 or indicator.get('trend') == 'worsening':
                scheduled = datetime.now() + timedelta(days=1)
                title = f"{indicator['name']}严重异常，请尽快就医"
                priority = "critical"
            else:
                scheduled = datetime.now() + timedelta(days=3)
                title = f"{indicator['name']}需复查"
                priority = "high"

        reminder = Reminder(
            member_id=member_id,
            type="review",
            title=title,
            scheduled_date=scheduled.date(),
            priority=priority,
            related_indicator=indicator["name"]
        )
        await self.save(reminder)
        return reminder

    async def get_daily_digest(self, member_id: str) -> dict:
        """生成每日待办合并推送"""
        today = datetime.now().date()
        reminders = await self.get_pending(member_id, today)

        # 按优先级排序
        critical = [r for r in reminders if r.priority == "critical"]
        high = [r for r in reminders if r.priority == "high"]
        normal = [r for r in reminders if r.priority == "normal"]

        return {
            "date": today.isoformat(),
            "total": len(reminders),
            "critical_count": len(critical),
            "items": critical + high + normal,
            "summary": self._generate_summary(critical, high, normal)
        }
```

```python
# app/tasks/reminder_task.py
from celery import shared_task
from celery.schedules import crontab
from app.services.reminder_service import ReminderService
from app.services.ws_manager import ws_manager

# 微信小程序订阅消息模板ID配置
SUBSCRIPTION_TEMPLATES = {
    "daily_digest": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",      # 每日待办摘要
    "urgent_alert": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",      # 紧急提醒（严重异常/疫苗逾期）
    "review_reminder": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",   # 复查提醒
}

@shared_task
def send_daily_digest():
    """每天早上8:00发送合并待办（仅对已订阅用户推送微信消息，未订阅用户走WebSocket/应用内横幅）"""
    service = ReminderService()
    for member in MemberService.get_all_active():
        digest = service.get_daily_digest(member.id)
        if digest["total"] > 0:
            # 1. 微信小程序订阅消息（仅当用户已授权该模板）
            if member.subscription_status.get("daily_digest", False):
                WechatAPI.send_subscribe_message(
                    member.openid,
                    template_id="daily_digest",
                    data={"thing1": digest["summary"], "time2": digest["date"]}
                )
            # 2. WebSocket推送（在线用户，无论是否订阅）
            ws_manager.send_to_member(member.id, {
                "type": "daily_digest",
                "payload": digest
            })
            # 3. 未订阅用户：写入 Redis 待办横幅，下次打开小程序时首页展示
            if not member.subscription_status.get("daily_digest", False):
                redis.setex(f"pending_digest:{member.id}", 86400, json.dumps(digest))

# Celery Beat 定时配置
celery_app.conf.beat_schedule = {
    "daily-digest": {
        "task": "app.tasks.reminder_task.send_daily_digest",
        "schedule": crontab(hour=8, minute=0),
    },
    "check-overdue-reminders": {
        "task": "app.tasks.reminder_task.check_overdue",
        "schedule": crontab(hour="*/1"),  # 每小时
    }
}
```

---

## 十一、家庭成员共享

```python
# app/services/member_service.py
import secrets
from app.models.family import Family
from app.models.member import Member

class MemberService:
    async def create_family(self, admin_name: str, admin_info: dict) -> Family:
        """创建家庭并返回邀请信息"""
        family = Family(
            name=f"{admin_name}的家庭",
            invite_code=secrets.token_urlsafe(8)[:6].upper()  # 6位邀请码
        )
        await family.save()

        admin = Member(
            family_id=family.id,
            role="creator",
            **admin_info
        )
        await admin.save()
        family.admin_id = admin.id
        await family.save()

        return family, admin

    async def generate_invite_link(self, family_id: str) -> str:
        """生成微信分享链接（含临时JWT）"""
        family = await Family.get(family_id)
        token = create_jwt({"family_id": family_id, "type": "invite"}, expires_hours=168)
        return f"https://api.health-helper.example.com/join?token={token}"

    async def update_subscription(self, member_id: str, subscriptions: dict) -> Member:
        """更新用户微信订阅状态
        subscriptions: {"daily_digest": true, "urgent_alert": false, ...}
        """
        member = await Member.get(member_id)
        current = member.subscription_status or {}
        current.update(subscriptions)
        member.subscription_status = current
        await member.save()
        return member

    async def join_by_link(self, token: str, user_info: dict) -> Member:
        """通过分享链接加入家庭"""
        payload = decode_jwt(token)
        if payload.get("type") != "invite":
            raise ValueError("无效邀请链接")

        family_id = payload["family_id"]
        member = Member(
            family_id=family_id,
            role="member",
            name=user_info.get("nickname", "家人"),
            **user_info
        )
        await member.save()

        # 通知管理员
        family = await Family.get(family_id)
        ws_manager.send_to_member(family.admin_id, {
            "type": "member_joined",
            "member_name": member.name
        })

        return member
```

```python
# app/routers/members.py — 订阅状态更新接口
from fastapi import APIRouter, Depends
from app.dependencies import get_current_member
from app.services.member_service import MemberService

router = APIRouter()

@router.put("/me/subscription")
async def update_subscription(
    subscriptions: dict,
    member: Member = Depends(get_current_member)
):
    """更新用户微信订阅消息授权状态"""
    updated = await MemberService.update_subscription(member.id, subscriptions)
    return {"subscription_status": updated.subscription_status}
```

---

## 十二、数据导出

```python
# app/services/export_service.py
import io
import openpyxl
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

class ExportService:
    async def export_excel(self, member_id: str, start_date: str, end_date: str) -> bytes:
        """导出指标数据为Excel"""
        indicators = await IndicatorService.get_range(member_id, start_date, end_date)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "指标记录"

        # 表头
        headers = ["日期", "指标名称", "数值", "单位", "参考范围", "状态"]
        ws.append(headers)

        # 数据
        for item in indicators:
            ws.append([
                item.date, item.indicator_name, item.value,
                item.unit, f"{item.lower_limit}-{item.upper_limit}", item.status
            ])

        # 状态列颜色标记
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
            status_cell = row[5]
            if status_cell.value == "normal":
                status_cell.fill = openpyxl.styles.PatternFill(start_color="ECFDF5", end_color="ECFDF5", fill_type="solid")
            elif status_cell.value in ["low", "high"]:
                status_cell.fill = openpyxl.styles.PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
            elif status_cell.value == "critical":
                status_cell.fill = openpyxl.styles.PatternFill(start_color="FEF2F2", end_color="FEF2F2", fill_type="solid")

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.read()

    async def generate_medical_summary(self, member_id: str, hospital_id: str = None) -> bytes:
        """生成就诊摘要PDF"""
        member = await MemberService.get(member_id)
        abnormalities = await IndicatorService.get_recent_abnormal(member_id, days=30)

        # 调用AI生成摘要文本
        context = {"member": member, "abnormalities": abnormalities}
        provider = ProviderFactory.get_provider("kimi")
        summary = await provider.generate_summary(context)

        # 生成PDF
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setFont("SimSun", 16)  # 需要嵌入中文字体
        c.drawString(100, 800, f"{member.name} 的就诊摘要")
        c.setFont("SimSun", 12)

        y = 760
        for line in summary.split("\n"):
            c.drawString(100, y, line)
            y -= 20
            if y < 100:
                c.showPage()
                y = 800

        c.save()
        buffer.seek(0)
        return buffer.read()
```

---

## 十三、自动清理任务

```python
# app/tasks/cleanup_task.py
from sqlalchemy import delete
from datetime import datetime, timedelta
import asyncio

@shared_task
def cleanup_expired_data():
    """每日凌晨3点执行数据清理 — 分批删除避免锁表"""
    BATCH_SIZE = 1000

    async def _cleanup():
        # 1. 分批清理 90 天前的 AI 对话
        while True:
            result = await db.execute(
                delete(AIConversation)
                .where(AIConversation.updated_at < datetime.now() - timedelta(days=90))
                .limit(BATCH_SIZE)
            )
            if result.rowcount == 0:
                break
            await asyncio.sleep(1)  # 批次间 sleep，降低主库压力

        # 2. 分批清理 1 年前的软删除成员
        while True:
            result = await db.execute(
                delete(Member)
                .where(Member.deleted_at < datetime.now() - timedelta(days=365))
                .limit(BATCH_SIZE)
            )
            if result.rowcount == 0:
                break
            await asyncio.sleep(1)

        # 3. 清理 24 小时前的导出临时文件（文件系统操作，无需分批）
        ExportService.cleanup_temp_files(max_age_hours=24)

    async_to_sync(_cleanup)()
```
