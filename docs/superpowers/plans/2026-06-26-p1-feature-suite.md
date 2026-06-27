# P1 核心体验增强技术方案

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Note:** 本方案覆盖 7 个相对独立的 P1 能力。实际落地时建议拆分为 4 个子计划独立执行：AI 子系统（全局悬浮球 + 动态快捷问题 + 报告摘要）、指标子系统（趋势图 Bottom Sheet + 多指标对比）、用药/提醒子系统（用药日历 + 漏服提醒 + 提醒自动触发）、疫苗/报告子系统（标准疫苗库 + 逾期计算 + 报告一键提醒）。本文件作为统一技术总览，定义跨模块接口与开发节奏。

**Goal:** 为 Care Assist 补齐 7 个 P1 体验增强能力：全局 AI 悬浮球、动态 AI 快捷问题、趋势图 Bottom Sheet / 多指标对比、用药打卡日历与漏服提醒、提醒系统自动触发、标准疫苗库与逾期计算、报告 AI 摘要与一键提醒。

**Architecture:** 后端沿用 FastAPI + SQLAlchemy async，新增 Celery Beat 定时任务预生成用药日志并扫描逾期提醒/疫苗/用药；AI 能力复用现有 `AIService` 与 Kimi Code Provider；前端沿用原生微信小程序，新增全局 AI 悬浮球组件、用药日历组件、趋势图 Bottom Sheet 组件，统一通过 `utils/api.js` 调用后端。

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0 async, aiomysql, Celery, Redis, Pydantic; 微信小程序 WXML/WXSS/JS; ECharts/Canvas（趋势图）。

## 全局约束

- Python 版本：>=3.11
- 后端框架：FastAPI >=0.110.0
- ORM：SQLAlchemy 2.0 async
- 数据库：MySQL 8.0+（开发环境 `tests/conftest.py` 默认端口 3308）
- 前端：原生微信小程序，不使用第三方框架
- 测试：pytest + pytest-asyncio，TDD 风格，每个任务先有测试再实现
- 代码风格：ruff line-length 100，mypy strict
- 提交规范：`feat(scope): description`，结尾加 `Co-Authored-By: Claude <noreply@anthropic.com>`
- 环境变量敏感信息（API key）不得提交到 git，统一走 `.env`
- 所有新增 API 必须添加到 `app/main.py` 注册路由
- 所有新增数据模型必须通过 Alembic 生成迁移脚本
- 所有定时任务必须幂等，失败可重试，不依赖本地状态

---

## 方案修正说明（基于代码库实际状态复核）

经过对 `backend/app/`、`miniprogram/` 和测试目录的实际代码复核，原方案存在以下理解偏差或遗漏，需要在执行前修正：

1. **ReminderRule 模型与扫描引擎脱节（Task 1.2）**
   - 原计划引入 `ReminderRule` 作为提醒规则模型，但 Task 4.2 的漏服/逾期扫描引擎直接扫描 `MedicationLog` / `VaccineRecord` / `Reminder`，并未使用 `ReminderRule`。
   - **修正**：P1 阶段移除 `ReminderRule`，扫描引擎直接基于业务模型生成提醒。如需可配置规则，留到 P2 再抽象。

2. **漏服检测缺少 MedicationLog 日常生成机制（Task 4.2）**
   - 当前 `MedicationLog` 只在用户打卡（`POST /medications/{id}/take`）时 upsert，没有每日预生成 `pending` 记录。
   - 如果不存在 pending 记录，漏服扫描将永远为空转。
   - **修正**：新增 **Task 4.0 用药计划日志预生成**，在每日 Celery 任务中根据 `Medication.time_slots` 为每个服药日生成 `pending` 的 `MedicationLog`；同时日历 API 在查询时做兜底生成。

3. **Celery 任务中直接使用 `asyncio.run()` 的隐患（Task 1.1 / 4.2）**
   - 原计划示例直接 `asyncio.run(_run())`，在 Celery sync worker 里可行，但复用 `app.db.session.async_session` 时需注意事件循环生命周期；测试环境若已存在 loop 会抛 `RuntimeError`。
   - **修正**：所有 Celery 任务统一通过 `app.tasks.utils.run_async_task(coro)` 包装，内部兼容已存在事件循环的情况。

4. **`utils/api.js` 导出方式错误（多个前端 Task）**
   - 原计划示例写 `module.exports.compareIndicators = compareIndicators`，会覆盖 `api.js` 已有的导出对象，导致 `get/post/put/del/uploadFile` 全部丢失。
   - **修正**：在 `api.js` 现有的 `module.exports = { get, post, put, del, uploadFile }` 对象中新增方法，或单独提供 `utils/api-ext.js`。

5. **疫苗排期去重逻辑过粗（Task 5.1）**
   - 原计划 `if existing.scalars().first(): return []` 只要存在任何疫苗记录就跳过全部排期，导致无法为新增儿童补生成。
   - **修正**：按 `(member_id, vaccine_name, dose)` 去重，仅跳过已存在的剂次。

6. **全局 AI 悬浮球与 `app.js` 的矛盾描述（Task 2.1）**
   - 原计划文件列表写“Modify: `miniprogram/app.js`（无代码改动，仅说明）”，后续又写“`app.js` 注册全局 AI-FAB”。
   - **修正**：`app.js` 无需改动；全局组件只需在 `app.json` 注册 `usingComponents`，并在每个 page.wxml 中引用。`app.wxss` 统一定位样式，`utils/page-base.js` 提供 `onAIFabTap`。

7. **MedicationLog 状态校验缺失**
   - 当前模型 `status` 为普通字符串，仅计划文档注释合法值。
   - **修正**：新增 Pydantic schema 校验 `MedicationLogCreate/Update` 的 `status ∈ {pending, taken, missed, skipped}`；模型层仍用 String 以保持灵活，但 API 层必须校验。

8. **报告 AI 摘要的 `report.ai_summary` 字段已存在**
   - 模型已有 `ai_summary: Mapped[str | None]`，只是从未写入。方案无需新增模型字段，只需新增 API 与 `AIService.summarize_report`。

9. **`_build_report_summary_prompt` 无需 async**
   - 只是拼接字符串，应改为同步方法，避免无意义 `await`。

10. **Celery Beat 5 分钟间隔偏激进**
    - 开发环境 5 分钟可接受，生产建议改为可配置（默认 1 小时），避免频繁扫描。

---

## P0 已完成基线（2026-06-26）

本次 P1 方案之前，以下 P0 核心功能已落地：

- 指标矩阵视图：`/api/indicators/matrix` + 前端 indicators 页面矩阵切换。
- 手动录入指标：`/api/indicators/metadata` + `indicator-manual` 页面 + OCR 失败兜底。
- 慢性病专区：`/api/indicators/chronic/*` + `chronic` 页面。
- 儿童成长与发育：`GrowthRecord` 模型 + `/api/child/*` + `growth` / `milestone` 页面。
- 真实 OCR Pipeline：`OCRProvider` 抽象 + Baidu/Tencent/Mock 注册 + `ocr_pipeline.py`。

## 当前状态评估

| 能力 | 现有基础 | 缺失部分 | 备注 |
|------|----------|----------|------|
| 全局 AI 悬浮球 | AI 对话 API 已存在（`/api/ai-conversations`），`AIService` 已接入 Kimi Code；AI 页有静态快捷问题 | 无全局悬浮球组件；快捷问题硬编码 | `app.json` 无 `usingComponents`，全局组件需逐页注册 |
| 动态 AI 快捷问题 | `AIService` 有 `generate_reply` / `generate_family_summary`，无专用快捷问题逻辑 | 无 `/quick-questions` 接口；无页面上下文推荐 | 原计划提到 `_generate_mock_reply` 关键词匹配，实际该方法是完整规则回复生成器，非快捷问题专用 |
| 趋势图 Bottom Sheet / 多指标对比 | `/api/indicators/trend` 已存在；`/api/indicators/matrix` 已完成 | 无 `/compare` 多指标对比 API；无 Bottom Sheet 组件 | 矩阵视图已落地，可复用其数据聚合思路 |
| 用药打卡日历与漏服提醒 | `Medication` / `MedicationLog` 模型与 CRUD 已存在；`POST /{id}/take` 已存在 | 无 `/calendar` 聚合接口；`MedicationLog.status` 未验证 `missed`/`skipped`；无日历组件 | 当前 `MedicationLog.status` 默认 `pending`，无字段级枚举校验 |
| 提醒系统自动触发 | `Reminder` 模型与 CRUD 已存在 | **无 Celery 基础设施**；无扫描引擎；不会自动生成提醒；`MedicationLog` 未每日预生成，漏服扫描无数据 | Celery 完全未配置，仅有 `REDIS_URL`；建议 P1 直接扫描业务模型，不抽象 `ReminderRule` |
| 标准疫苗库与逾期计算 | `VaccineRecord` 模型与 CRUD 已存在；`seed.py` 有静态字典 | 无 `VaccineLibrary` 模型；`seed_all()` 是 no-op；无 `/schedule` 排期接口；无逾期扫描 | `seed.py` 中 `VACCINE_SCHEDULES` 未写入数据库 |
| 报告 AI 摘要与一键提醒 | `Report` 模型有 `ai_summary` 字段；OCR Pipeline 已完成；`pkg-system/pages/report-detail` 已存在 | `ai_summary` 未填充；无 `/api/reports/{id}/ai-summary`；无 `/api/reminders/from-report` | `report-detail.wxml` 已预留 AI 摘要展示卡片，但无生成按钮 |

---

## 文件结构总览

### 后端新增/修改

```
backend/app/
├── api/
│   ├── ai_conversations.py       # 新增 /quick-questions, /stream（P1-1/2/7）
│   ├── indicators.py             # 新增 /compare（多指标对比 P1-3）
│   ├── medications.py            # 新增 /calendar（用药日历 P1-4）
│   ├── reminders.py              # 新增 /generate-from-event（一键提醒 P1-7）
│   ├── vaccines.py               # 新增 /schedule, /overdue（P1-6）
│   └── reports.py                # 新增 /{id}/ai-summary（P1-7）
├── core/
│   ├── ai_service.py             # 新增 generate_quick_questions, summarize_report
│   └── reminder_engine.py        # 新增逾期/漏服扫描逻辑（P1-4/5/6）
├── models/
│   ├── vaccine_library.py        # 标准疫苗库模型（P1-6）
│   └── medication.py             # 补充 missed/skipped 状态说明与索引（P1-4）
├── schemas/
│   ├── ai_conversation.py        # 新增 QuickQuestionsOut, AIStreamChunk
│   ├── indicator.py              # 新增 IndicatorCompareOut
│   ├── medication.py             # 新增 MedicationCalendarOut, MedicationCalendarDay
│   ├── reminder.py               # 新增 ReminderGenerateRequest
│   ├── vaccine.py                # 新增 VaccineLibraryOut, VaccineScheduleOut
│   └── report.py                 # 新增 ReportAISummaryOut
├── services/
│   ├── reminder_service.py       # 提醒创建/扫描/触发编排（P1-4/5/6/7）
│   └── medication_log_service.py # 每日用药日志预生成（P1-4）
├── tasks/
│   ├── __init__.py
│   ├── utils.py                  # Celery 中运行 async 代码的兼容包装
│   └── cron.py                   # Celery 定时任务定义（P1-5）
├── celery_app.py                 # Celery 应用实例（P1-5）
└── config.py                     # 新增 CELERY_BROKER_URL, CELERY_BEAT_SCHEDULE
```

### 前端新增/修改

```
miniprogram/
├── components/
│   ├── ai-fab/                   # 全局 AI 悬浮球（P1-1）
│   │   ├── ai-fab.js
│   │   ├── ai-fab.wxml
│   │   └── ai-fab.wxss
│   ├── ai-quick-questions/       # 快捷问题面板（P1-2）
│   │   ├── ai-quick-questions.js
│   │   ├── ai-quick-questions.wxml
│   │   └── ai-quick-questions.wxss
│   ├── trend-bottom-sheet/       # 趋势图 Bottom Sheet（P1-3）
│   │   ├── trend-bottom-sheet.js
│   │   ├── trend-bottom-sheet.wxml
│   │   └── trend-bottom-sheet.wxss
│   └── medication-calendar/      # 用药打卡日历（P1-4）
│       ├── medication-calendar.js
│       ├── medication-calendar.wxss
│       └── medication-calendar.wxml
├── pages/
│   └── indicators/
│       ├── indicators.js         # 集成多指标对比入口（P1-3）
│       └── indicators.wxml
├── pkg-medication/
│   └── pages/
│       ├── medication/
│       │   ├── medication.js     # 集成日历与打卡（P1-4）
│       │   └── medication.wxml
│       └── medication-add/       # 新增用药时可选标准库（无标准用药库时不阻塞）
├── pkg-child/
│   └── pages/
│       └── vaccine/
│           ├── vaccine.js        # 集成标准疫苗库与逾期（P1-6）
│           └── vaccine.wxml
├── pkg-system/
│   └── pages/
│       └── report-detail/        # 新增 AI 摘要 + 一键提醒（P1-7）
│           ├── report-detail.js
│           └── report-detail.wxml
├── app.js                        # 注册全局 AI-FAB（P1-1）
└── utils/
    └── api.js                    # 新增对应 API 封装
```

---

## Phase 1：共享基础设施

所有后续能力依赖此阶段。先完成数据模型扩展、迁移、Celery 任务框架和通用引擎。

### Task 1.1：Celery 任务框架

**Files:**
- Create: `backend/app/celery_app.py`
- Create: `backend/app/tasks/__init__.py`
- Create: `backend/app/tasks/utils.py`
- Create: `backend/app/tasks/cron.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/main.py`（健康检查无需改动）
- Test: `backend/tests/unit/test_celery_tasks.py`

**Interfaces:**
- Consumes: `REDIS_URL` from config
- Produces: `celery_app` instance; `run_async_task` helper; `scan_overdue_reminders`, `scan_missed_medications`, `scan_overdue_vaccines`, `generate_medication_logs` task signatures

- [ ] **Step 1：添加 Celery 配置到 `app/config.py`**

```python
CELERY_BROKER_URL: str = ""
CELERY_RESULT_BACKEND: str = ""
```

默认值空字符串表示本地开发不强制启动 worker；`celery_app.py` 中若为空则使用 `REDIS_URL` 兜底。

- [ ] **Step 2：创建 `app/celery_app.py`**

```python
from celery import Celery
from app.config import settings

broker = settings.CELERY_BROKER_URL or settings.REDIS_URL
backend = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL

celery_app = Celery("care_assist", broker=broker, backend=backend)
celery_app.conf.update(
    timezone="Asia/Shanghai",
    enable_utc=True,
    beat_schedule={},
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)
```

- [ ] **Step 3：创建 `app/tasks/utils.py` 兼容 async 执行**

```python
import asyncio
from typing import Any, Coroutine


def run_async_task(coro: Coroutine[Any, Any, Any]) -> Any:
    """Run an async coroutine from a synchronous Celery task.

    Celery workers run sync code; this helper safely starts a new event loop
    when none exists, or reuses the current loop in test environments.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Nested event loop (e.g. pytest-asyncio): schedule and wait via run_in_executor
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)
```

> 注：`nest_asyncio` 需加入 `requirements.txt` / `pyproject.toml`；若测试不触发 Celery 任务，可仅在 dev 依赖中声明。

- [ ] **Step 4：创建 `app/tasks/cron.py` 任务桩**

```python
from app.celery_app import celery_app

@celery_app.task(name="care_assist.scan_overdue_reminders")
def scan_overdue_reminders() -> dict:
    return {"scanned": 0, "updated": 0}

@celery_app.task(name="care_assist.scan_missed_medications")
def scan_missed_medications() -> dict:
    return {"scanned": 0, "missed": 0}

@celery_app.task(name="care_assist.scan_overdue_vaccines")
def scan_overdue_vaccines() -> dict:
    return {"scanned": 0, "overdue": 0}

@celery_app.task(name="care_assist.generate_medication_logs")
def generate_medication_logs() -> dict:
    return {"generated": 0}
```

- [ ] **Step 5：写测试验证任务可导入**

```python
def test_celery_tasks_importable():
    from app.tasks.cron import scan_overdue_reminders
    result = scan_overdue_reminders.run()
    assert result["scanned"] == 0
```

- [ ] **Step 6：运行测试并提交**

Run: `cd backend && pytest tests/unit/test_celery_tasks.py -v`
Expected: PASS

Commit: `feat(infra): add celery task framework for scheduled scans`

### Task 1.2：提醒规则模型（P1 可选 / 建议跳过）

> **修正说明**：原方案引入 `ReminderRule` 但 Task 4.2 的扫描引擎并未使用它。P1 建议直接基于 `Medication` / `VaccineRecord` / `Reminder` 扫描生成提醒，避免过度设计。本任务保留为可选，团队若需要“可配置提醒规则”再实现。

**Files（若执行）：**
- Create: `backend/app/models/reminder_rule.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/XXXX_add_reminder_rules.py`
- Test: `backend/tests/unit/test_reminder_rule_model.py`

**默认跳过方式**：
- 不创建 `ReminderRule` 模型与迁移。
- 在迭代 1 验收中不检查本任务测试。
- 后续若启用，再重构 `ReminderEngine` 从 `ReminderRule` 生成提醒。

### Task 1.3：标准疫苗库模型与种子数据

**Files:**
- Create: `backend/app/models/vaccine_library.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/db/seed.py`（已存在则修改）
- Create: `backend/alembic/versions/XXXX_add_vaccine_library.py`
- Test: `backend/tests/unit/test_vaccine_library.py`

**Interfaces:**
- Consumes: None
- Produces: `VaccineLibrary` model; `seed_vaccine_library(session)` function

- [ ] **Step 1：定义 `VaccineLibrary` 模型**

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Index, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

class VaccineLibrary(Base):
    __tablename__ = "vaccine_library"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    dose_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    recommended_age_months: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # 国家免疫规划 / 自费 / 特殊人群
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    disease: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_vaccine_lib_age", "recommended_age_months"),
        Index("idx_vaccine_lib_name_dose", "name", "dose_number"),
    )
```

- [ ] **Step 2：创建种子函数 `app/db/seed.py`**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.vaccine_library import VaccineLibrary

VACCINE_LIBRARY_SEED = [
    {"name": "乙肝疫苗", "dose_number": 1, "recommended_age_months": 0, "category": "国家免疫规划", "disease": "乙型肝炎"},
    {"name": "卡介苗", "dose_number": 1, "recommended_age_months": 0, "category": "国家免疫规划", "disease": "结核病"},
    {"name": "脊髓灰质炎疫苗", "dose_number": 1, "recommended_age_months": 2, "category": "国家免疫规划", "disease": "脊髓灰质炎"},
    {"name": "脊髓灰质炎疫苗", "dose_number": 2, "recommended_age_months": 3, "category": "国家免疫规划", "disease": "脊髓灰质炎"},
    {"name": "百白破疫苗", "dose_number": 1, "recommended_age_months": 3, "category": "国家免疫规划", "disease": "百日咳/白喉/破伤风"},
    {"name": "麻腮风疫苗", "dose_number": 1, "recommended_age_months": 8, "category": "国家免疫规划", "disease": "麻疹/腮腺炎/风疹"},
    {"name": "乙脑减毒活疫苗", "dose_number": 1, "recommended_age_months": 8, "category": "国家免疫规划", "disease": "流行性乙型脑炎"},
    {"name": "甲肝疫苗", "dose_number": 1, "recommended_age_months": 18, "category": "国家免疫规划", "disease": "甲型肝炎"},
]

async def seed_vaccine_library(db: AsyncSession) -> int:
    from sqlalchemy import select
    existing = await db.execute(select(VaccineLibrary.name).limit(1))
    if existing.scalar_one_or_none():
        return 0
    for item in VACCINE_LIBRARY_SEED:
        db.add(VaccineLibrary(**item))
    await db.commit()
    return len(VACCINE_LIBRARY_SEED)
```

- [ ] **Step 3：生成迁移并写测试**

Run: `cd backend && alembic revision --autogenerate -m "add vaccine_library table"`

```python
import pytest
from app.models.vaccine_library import VaccineLibrary
from app.db.seed import seed_vaccine_library

@pytest.mark.asyncio
async def test_seed_vaccine_library(db):
    count = await seed_vaccine_library(db)
    assert count == 8
    count2 = await seed_vaccine_library(db)
    assert count2 == 0
```

- [ ] **Step 4：运行测试并提交**

Run: `pytest tests/unit/test_vaccine_library.py -v`
Expected: PASS

Commit: `feat(vaccine): add vaccine library model and seed data`

---

## Phase 2：AI 子系统（P1-1 / P1-2 / P1-7 摘要部分）

### Task 2.1：全局 AI 悬浮球前端组件

**Files:**
- Create: `miniprogram/components/ai-fab/ai-fab.js`
- Create: `miniprogram/components/ai-fab/ai-fab.wxml`
- Create: `miniprogram/components/ai-fab/ai-fab.wxss`
- Create: `miniprogram/components/ai-fab/ai-fab.json`
- Modify: `miniprogram/app.json`（注册全局 usingComponents）
- Modify: `miniprogram/app.wxss`（全局定位样式）
- Create: `miniprogram/utils/page-base.js`（提供 `onAIFabTap` 方法）
- Test: `miniprogram/components/ai-fab/ai-fab.test.js`（可选，以真机/开发者工具测试为主）

**Interfaces:**
- Consumes: `store.currentMember`, `store.token`
- Produces: `tap` event with `{ pageContext: string }`

- [ ] **Step 1：创建组件 `ai-fab.json`**

```json
{
  "component": true,
  "usingComponents": {}
}
```

- [ ] **Step 2：实现 `ai-fab.wxml`**

```xml
<view class="ai-fab" style="bottom: {{safeBottom + 80}}px;" bindtap="onTap">
  <image class="ai-fab-icon" src="/assets/icons/ai.png" />
</view>
```

- [ ] **Step 3：实现 `ai-fab.wxss`**

```css
.ai-fab {
  position: fixed;
  right: 16px;
  width: 56px;
  height: 56px;
  border-radius: 28px;
  background: #2563EB;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.ai-fab-icon { width: 28px; height: 28px; }
```

- [ ] **Step 4：实现 `ai-fab.js`**

```javascript
const { store } = require('../../utils/store')

Component({
  data: { safeBottom: 0 },
  lifetimes: {
    attached() {
      const sys = wx.getSystemInfoSync()
      this.setData({ safeBottom: sys.safeAreaInsetBottom || 0 })
    }
  },
  methods: {
    onTap() {
      const pages = getCurrentPages()
      const route = pages.length ? `/${pages[pages.length - 1].route}` : ''
      this.triggerEvent('tap', { pageContext: route })
    }
  }
})
```

- [ ] **Step 5：在 `app.json` 注册全局 usingComponents**

```json
{
  "pages": [ ... ],
  "usingComponents": {
    "ai-fab": "./components/ai-fab/ai-fab"
  }
}
```

> `app.js` 无需改动。全局组件注册后，仍需在每个 page.wxml 中显式引用。

- [ ] **Step 6：在每个页面模板中引用悬浮球**

微信小程序不支持在 `app.wxml` 定义全局 slot，需在每个 `page.wxml` 底部加入：

```xml
<ai-fab bind:tap="onAIFabTap" />
```

为减少重复，在 `app.wxss` 统一定位样式，并通过 `utils/page-base.js` 提供公共 `onAIFabTap` 方法供各页面混入。

- [ ] **Step 7：创建 `miniprogram/utils/page-base.js`**

```javascript
function onAIFabTap(e) {
  const ctx = e.detail.pageContext || ''
  wx.navigateTo({
    url: `/pages/ai/ai?pageContext=${encodeURIComponent(ctx)}`
  })
}

module.exports = { onAIFabTap }
```

- [ ] **Step 8：提交**

Commit: `feat(ui): add global AI floating ball component`

### Task 2.2：动态 AI 快捷问题接口

**Files:**
- Modify: `backend/app/core/ai_service.py`
- Modify: `backend/app/api/ai_conversations.py`
- Modify: `backend/app/schemas/ai_conversation.py`
- Test: `backend/tests/unit/test_ai_quick_questions.py`

**Interfaces:**
- Consumes: `page_context: str`, `member: Member`, `recent_indicators`, `recent_reports`
- Produces: `list[str]` of quick question texts

- [ ] **Step 1：扩展 `AIService` 方法**

```python
async def generate_quick_questions(
    self,
    member: Member,
    page_context: Optional[str] = None,
    recent_indicators: Optional[list[dict]] = None,
    recent_reports: Optional[list[dict]] = None,
) -> list[str]:
    provider = self._get_provider()
    if provider is not None:
        try:
            return await self._call_provider_for_questions(
                provider, member, page_context, recent_indicators, recent_reports
            )
        except Exception:
            pass
    return self._rule_based_quick_questions(member, page_context, recent_indicators, recent_reports)
```

- [ ] **Step 2：实现规则分支**

```python
QUICK_QUESTION_TEMPLATES = {
    "pages/home/home": ["{name}最近指标怎么样？", "今天需要关注哪些健康提醒？"],
    "pages/indicators/indicators": ["{name}的血压趋势如何？", "哪些指标需要特别关注？"],
    "pages/reports/reports": ["帮我解读{name}最新报告", "报告中有哪些异常指标？"],
    "pages/medication/medication": ["{name}今天吃药了吗？", "最近漏服过药吗？"],
    "pages/vaccine/vaccine": ["{name}下一针疫苗什么时候打？", "有没有逾期的疫苗？"],
}

def _rule_based_quick_questions(self, member, page_context, recent_indicators, recent_reports):
    base = self.QUICK_QUESTION_TEMPLATES.get(page_context or "", ["{name}最近身体怎么样？"])
    if recent_indicators:
        base.append("{name}最近指标有什么变化？")
    if recent_reports:
        base.append("帮我总结{name}最近的检查报告")
    return [q.format(name=member.name) for q in base[:4]]
```

- [ ] **Step 3：新增数据拉取辅助函数与 API endpoint**

在 `backend/app/api/ai_conversations.py` 中新增：

```python
from sqlalchemy import select, desc
from app.models.indicator import IndicatorData
from app.models.report import Report

async def _get_recent_indicators(db: AsyncSession, member_id: str, limit: int = 5) -> list[dict]:
    stmt = (
        select(IndicatorData)
        .where(IndicatorData.member_id == member_id)
        .order_by(desc(IndicatorData.record_date), desc(IndicatorData.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [
        {
            "indicator_key": r.indicator_key,
            "indicator_name": r.indicator_name,
            "value": float(r.value),
            "unit": r.unit,
            "status": r.status,
            "record_date": str(r.record_date),
        }
        for r in result.scalars().all()
    ]

async def _get_recent_reports(db: AsyncSession, member_id: str, limit: int = 3) -> list[dict]:
    stmt = (
        select(Report)
        .where(Report.member_id == member_id)
        .order_by(desc(Report.report_date))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [
        {"id": r.id, "type": r.type, "report_date": str(r.report_date), "ocr_status": r.ocr_status}
        for r in result.scalars().all()
    ]
```

然后新增 endpoint：

```python
@router.get("/quick-questions", response_model=ResponseWrapper[list[str]])
async def get_quick_questions(
    member_id: str = Query(...),
    page_context: Optional[str] = Query(None),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    target = await _verify_member_in_family(member_id, current, db)
    recent_indicators = await _get_recent_indicators(db, target.id, limit=5)
    recent_reports = await _get_recent_reports(db, target.id, limit=3)
    ai_svc = AIService()
    questions = await ai_svc.generate_quick_questions(
        member=target,
        page_context=page_context,
        recent_indicators=recent_indicators or None,
        recent_reports=recent_reports or None,
    )
    return ResponseWrapper(data=questions)
```

- [ ] **Step 4：写测试**

```python
import pytest
from app.core.ai_service import AIService

@pytest.mark.asyncio
async def test_rule_based_quick_questions():
    from unittest.mock import MagicMock
    member = MagicMock()
    member.name = "张三"
    svc = AIService()
    qs = svc._rule_based_quick_questions(member, "pages/home/home", [], [])
    assert any("张三" in q for q in qs)
```

- [ ] **Step 5：运行测试并提交**

Run: `pytest tests/unit/test_ai_quick_questions.py tests/integration/test_ai_conversations.py -v`
Expected: PASS

Commit: `feat(ai): add dynamic quick questions API`

### Task 2.3：报告 AI 摘要

**Files:**
- Modify: `backend/app/core/ai_service.py`
- Modify: `backend/app/api/reports.py`
- Modify: `backend/app/schemas/report.py`
- Test: `backend/tests/unit/test_ai_report_summary.py`

**Interfaces:**
- Consumes: `report: Report`, `member: Member`, `extracted_indicators`
- Produces: `str` summary stored in `report.ai_summary`

- [ ] **Step 1：新增 `AIService.summarize_report`**

```python
async def summarize_report(self, member: Member, report: Report) -> str:
    provider = self._get_provider()
    extracted = report.extracted_indicators or []
    if provider is not None:
        try:
            prompt = self._build_report_summary_prompt(member, report, extracted)
            reply = await provider.chat([{"role": "user", "content": prompt}], stream=False, max_tokens=512, temperature=0.5)
            return self._append_disclaimer(reply)
        except Exception:
            pass
    return self._rule_based_summary(member, report, extracted)

def _build_report_summary_prompt(self, member, report, extracted):
    lines = [f"请用简洁中文总结{member.name}的{report.type}报告："]
    for item in extracted[:20]:
        lines.append(f"- {item.get('indicator_name')}: {item.get('value')} {item.get('unit')}")
    return "\n".join(lines)

async def _rule_based_summary(self, member, report, extracted):
    if not extracted:
        return f"{member.name}的{report.type}报告暂未识别到指标，请检查图片清晰度。"
    abnormal = [i for i in extracted if i.get("status") in ("low", "high", "critical")]
    names = "、".join(i["indicator_name"] for i in abnormal[:5])
    if abnormal:
        return f"{member.name}的报告中{name}等{len(abnormal)}项指标异常，建议进一步复查。"
    return f"{member.name}的报告中各项指标均在参考范围内，整体情况平稳。"
```

- [ ] **Step 2：新增报告摘要 API**

```python
@router.post("/{report_id}/ai-summary", response_model=ResponseWrapper[ReportOut])
async def generate_ai_summary(
    report_id: str,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    report = await db.get(Report, report_id)
    if not report:
        raise NotFoundException("报告不存在")
    target = await _verify_member_in_family(report.member_id, current, db)

    ai_svc = AIService()
    summary = await ai_svc.summarize_report(member=target, report=report)
    report.ai_summary = summary
    await db.commit()
    await db.refresh(report)
    return ResponseWrapper(data=ReportOut.model_validate(report))
```

- [ ] **Step 3：写测试**

```python
@pytest.mark.asyncio
async def test_rule_based_summary_no_indicators():
    from unittest.mock import MagicMock
    member = MagicMock(); member.name = "李四"
    report = MagicMock(); report.type = "lab"; report.extracted_indicators = []
    svc = AIService()
    text = await svc._rule_based_summary(member, report, [])
    assert "暂未识别" in text
```

- [ ] **Step 4：运行测试并提交**

Run: `pytest tests/unit/test_ai_report_summary.py -v`
Expected: PASS

Commit: `feat(ai): add report AI summary`

---

## Phase 3：指标子系统（P1-3）

### Task 3.1：多指标对比 API

**Files:**
- Modify: `backend/app/api/indicators.py`
- Modify: `backend/app/schemas/indicator.py`
- Test: `backend/tests/integration/test_indicators.py`（新增用例）

**Interfaces:**
- Consumes: `member_id`, `indicator_keys: list[str]`, `start_date`, `end_date`
- Produces: `IndicatorCompareOut` with series per indicator key

- [ ] **Step 1：新增 Schema**

```python
class IndicatorSeriesPoint(BaseModel):
    value: float
    record_date: date
    status: str

class IndicatorSeries(BaseModel):
    indicator_key: str
    indicator_name: str
    unit: str
    points: list[IndicatorSeriesPoint]

class IndicatorCompareOut(BaseModel):
    series: list[IndicatorSeries]
```

- [ ] **Step 2：新增 API endpoint**

```python
@router.get("/compare", response_model=ResponseWrapper[IndicatorCompareOut])
async def compare_indicators(
    member_id: str = Query(...),
    indicator_keys: list[str] = Query(default=[]),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    target = await _verify_member_in_family(member_id, current, db)
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=90)
    if not indicator_keys:
        return ResponseWrapper(data=IndicatorCompareOut(series=[]))

    stmt = (
        select(IndicatorData)
        .where(
            IndicatorData.member_id == member_id,
            IndicatorData.indicator_key.in_(indicator_keys),
            IndicatorData.record_date >= start_date,
            IndicatorData.record_date <= end_date,
        )
        .order_by(IndicatorData.record_date, IndicatorData.created_at)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    by_key: dict[str, list] = {k: [] for k in indicator_keys}
    names: dict[str, str] = {}
    units: dict[str, str] = {}
    for r in records:
        by_key[r.indicator_key].append(IndicatorSeriesPoint(
            value=float(r.value), record_date=r.record_date, status=r.status
        ))
        names[r.indicator_key] = r.indicator_name
        units[r.indicator_key] = r.unit

    series = [
        IndicatorSeries(
            indicator_key=k,
            indicator_name=names.get(k, k),
            unit=units.get(k, ""),
            points=by_key[k],
        )
        for k in indicator_keys
    ]
    return ResponseWrapper(data=IndicatorCompareOut(series=series))
```

- [ ] **Step 3：写集成测试**

```python
@pytest.mark.asyncio
async def test_compare_indicators(auth_client, test_member, db):
    from app.models.indicator import IndicatorData
    from decimal import Decimal
    db.add_all([
        IndicatorData(member_id=test_member.id, indicator_key="systolic_bp", indicator_name="收缩压", value=Decimal("120"), unit="mmHg", status="normal", record_date=date.today()),
        IndicatorData(member_id=test_member.id, indicator_key="diastolic_bp", indicator_name="舒张压", value=Decimal("80"), unit="mmHg", status="normal", record_date=date.today()),
    ])
    await db.commit()
    resp = await auth_client.get("/api/indicators/compare?member_id=" + test_member.id + "&indicator_keys=systolic_bp&indicator_keys=diastolic_bp")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["series"]) == 2
```

- [ ] **Step 4：运行测试并提交**

Run: `pytest tests/integration/test_indicators.py -v`
Expected: PASS

Commit: `feat(indicator): add multi-indicator comparison API`

### Task 3.2：趋势图 Bottom Sheet 前端组件

**Files:**
- Create: `miniprogram/components/trend-bottom-sheet/trend-bottom-sheet.js`
- Create: `miniprogram/components/trend-bottom-sheet/trend-bottom-sheet.wxml`
- Create: `miniprogram/components/trend-bottom-sheet/trend-bottom-sheet.wxss`
- Create: `miniprogram/components/trend-bottom-sheet/trend-bottom-sheet.json`
- Modify: `miniprogram/pages/indicators/indicators.js`
- Modify: `miniprogram/pages/indicators/indicators.wxml`
- Modify: `miniprogram/utils/api.js`

**Interfaces:**
- Consumes: `memberId`, `indicatorKeys`, `visible`
- Produces: `close` event

- [ ] **Step 1：新增 API 封装**

在 `miniprogram/utils/api.js` 的导出对象中新增方法：

```javascript
module.exports = {
  // ... existing get/post/put/del/uploadFile
  compareIndicators(memberId, indicatorKeys) {
    const keys = indicatorKeys.map(k => `indicator_keys=${encodeURIComponent(k)}`).join('&')
    return request({ url: `/api/indicators/compare?member_id=${memberId}&${keys}`, method: 'GET' })
  },
}
```

- [ ] **Step 2：实现组件 WXML**

```xml
<view class="mask {{visible ? 'show' : ''}}" bindtap="close">
  <view class="sheet" catchtap="noop">
    <view class="sheet-header">
      <text class="sheet-title">指标趋势</text>
      <text class="sheet-close" bindtap="close">✕</text>
    </view>
    <view class="sheet-body">
      <canvas type="2d" id="trendCanvas" class="trend-canvas"></canvas>
    </view>
  </view>
</view>
```

- [ ] **Step 3：实现组件 JS**

```javascript
const { compareIndicators } = require('../../utils/api')

Component({
  properties: {
    visible: Boolean,
    memberId: String,
    indicatorKeys: { type: Array, value: [] }
  },
  observers: {
    'visible,memberId,indicatorKeys': function(visible, memberId, indicatorKeys) {
      if (visible && memberId && indicatorKeys.length) {
        this.loadData()
      }
    }
  },
  methods: {
    async loadData() {
      const res = await compareIndicators(this.data.memberId, this.data.indicatorKeys)
      this.drawChart(res.data.series)
    },
    drawChart(series) {
      // 使用 wx-charts 或 canvas 自绘；为简化先占位绘制折线
      const query = wx.createSelectorQuery().in(this)
      query.select('#trendCanvas').fields({ node: true, size: true }).exec((res) => {
        const canvas = res[0].node
        const ctx = canvas.getContext('2d')
        const dpr = wx.getSystemInfoSync().pixelRatio
        canvas.width = res[0].width * dpr
        canvas.height = res[0].height * dpr
        ctx.scale(dpr, dpr)
        ctx.clearRect(0, 0, res[0].width, res[0].height)
        ctx.fillStyle = '#2563EB'
        ctx.font = '12px sans-serif'
        ctx.fillText(series.map(s => s.indicator_name).join(' / '), 10, 20)
      })
    },
    close() { this.triggerEvent('close') },
    noop() {}
  }
})
```

- [ ] **Step 4：在指标页集成**

```xml
<!-- miniprogram/pages/indicators/indicators.wxml -->
<trend-bottom-sheet visible="{{showTrend}}" member-id="{{memberId}}" indicator-keys="{{selectedKeys}}" bind:close="onTrendClose" />
```

- [ ] **Step 5：提交**

Commit: `feat(ui): add trend chart bottom sheet component`

---

## Phase 4：用药/提醒子系统（P1-4 / P1-5）

### Task 4.0：用药计划日志预生成

**Files:**
- Create: `backend/app/services/medication_log_service.py`
- Modify: `backend/app/tasks/cron.py`（注册每日生成任务）
- Modify: `backend/app/celery_app.py`（注册 beat schedule）
- Modify: `backend/app/api/medications.py`（日历 API 兜底调用）
- Test: `backend/tests/unit/test_medication_log_service.py`

**Interfaces:**
- Consumes: `Medication.time_slots`, `start_date`, `end_date`
- Produces: `MedicationLog` records with `status="pending"`

- [ ] **Step 1：实现 `MedicationLogService.generate_for_range`**

```python
from datetime import date, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.medication import Medication, MedicationLog

class MedicationLogService:
    @staticmethod
    async def generate_for_range(db: AsyncSession, member_id: str, start: date, end: date) -> int:
        """Idempotently generate pending MedicationLog entries for active medications."""
        stmt = (
            select(Medication)
            .where(Medication.member_id == member_id)
            .where(Medication.status == "active")
            .where(Medication.start_date <= end)
            .where((Medication.end_date.is_(None)) | (Medication.end_date >= start))
        )
        result = await db.execute(stmt)
        meds = result.scalars().all()

        created = 0
        for med in meds:
            for offset in range((end - start).days + 1):
                scheduled_date = start + timedelta(days=offset)
                if scheduled_date < med.start_date or (med.end_date and scheduled_date > med.end_date):
                    continue
                for slot in med.time_slots or []:
                    existing = await db.execute(
                        select(MedicationLog)
                        .where(MedicationLog.medication_id == med.id)
                        .where(MedicationLog.scheduled_date == scheduled_date)
                        .where(MedicationLog.scheduled_time == slot)
                    )
                    if existing.scalar_one_or_none():
                        continue
                    db.add(MedicationLog(
                        medication_id=med.id,
                        member_id=member_id,
                        scheduled_date=scheduled_date,
                        scheduled_time=slot,
                        status="pending",
                    ))
                    created += 1
        await db.commit()
        return created
```

- [ ] **Step 2：在 `cron.py` 注册每日任务**

```python
from app.services.medication_log_service import MedicationLogService
from app.db.session import async_session
from app.tasks.utils import run_async_task

@celery_app.task(name="care_assist.generate_medication_logs")
def generate_medication_logs() -> dict:
    async def _run():
        async with async_session() as db:
            # Generate logs for today + next 7 days for all members with active medications
            from sqlalchemy import select
            from app.models.medication import Medication
            result = await db.execute(select(Medication.member_id).where(Medication.status == "active").distinct())
            member_ids = result.scalars().all()
            today = date.today()
            end = today + timedelta(days=7)
            total = 0
            for member_id in member_ids:
                total += await MedicationLogService.generate_for_range(db, member_id, today, end)
            return total
    count = run_async_task(_run())
    return {"generated": count}
```

> 生产环境建议按家庭/成员分片，避免单次事务过大；开发环境上述实现足够。

- [ ] **Step 3：日历 API 兜底调用**

在 `GET /api/medications/calendar` 中，先调用 `MedicationLogService.generate_for_range(db, member_id, start, end)`，再查询日志。这样即使 Celery 未启动，日历也能看到数据。

- [ ] **Step 4：写测试**

```python
import pytest
from datetime import date
from app.services.medication_log_service import MedicationLogService
from app.models.medication import Medication, MedicationLog

@pytest.mark.asyncio
async def test_generate_for_range(db, test_member):
    med = Medication(
        member_id=test_member.id,
        name="测试药",
        dosage="1片",
        frequency="daily",
        time_slots=["08:00"],
        start_date=date(2020, 1, 1),
        status="active",
    )
    db.add(med); await db.flush()
    count = await MedicationLogService.generate_for_range(db, test_member.id, date(2020, 1, 1), date(2020, 1, 3))
    assert count == 3
    count2 = await MedicationLogService.generate_for_range(db, test_member.id, date(2020, 1, 1), date(2020, 1, 3))
    assert count2 == 0  # idempotent
```

- [ ] **Step 5：运行测试并提交**

Run: `pytest tests/unit/test_medication_log_service.py -v`
Expected: PASS

Commit: `feat(medication): add daily medication log generation service`

### Task 4.1：用药日历聚合 API

**Files:**
- Modify: `backend/app/api/medications.py`
- Modify: `backend/app/schemas/medication.py`（新增日历 schema 与 `MedicationLog` 状态校验）
- Modify: `backend/app/services/medication_log_service.py`（日历 API 兜底调用）
- Test: `backend/tests/integration/test_medications.py`

**Interfaces:**
- Consumes: `member_id`, `year_month` (YYYY-MM)
- Produces: `MedicationCalendarOut` with daily adherence status

- [ ] **Step 1：扩展 MedicationLog 状态校验**

模型层 `status` 保持 `String(20)` 不变（避免 Alembic 生成无意义迁移），在 Schema 层增加校验：

```python
from pydantic import field_validator

class MedicationLogUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in ("pending", "taken", "missed", "skipped"):
            raise ValueError("status must be one of: pending, taken, missed, skipped")
        return v
```

同时更新 `MedicationLogOut` 的文档注释，说明合法状态。

> 若团队希望数据库层也约束，可后续增加 `CheckConstraint` 迁移；P1 以 API 层校验为主。

- [ ] **Step 2：新增 Schema**

```python
class MedicationCalendarDay(BaseModel):
    date: date
    scheduled_count: int
    taken_count: int
    missed_count: int
    status: str  # complete / partial / missed / none

class MedicationCalendarOut(BaseModel):
    year: int
    month: int
    days: list[MedicationCalendarDay]
```

- [ ] **Step 3：新增 API endpoint**

```python
from calendar import monthrange
from app.services.medication_log_service import MedicationLogService

@router.get("/calendar", response_model=ResponseWrapper[MedicationCalendarOut])
async def get_medication_calendar(
    member_id: str = Query(...),
    year_month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    target = await _verify_member_in_family(member_id, current, db)
    year, month = map(int, year_month.split("-"))
    _, last_day = monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, last_day)

    # Ensure pending logs exist for the requested month (idempotent)
    await MedicationLogService.generate_for_range(db, member_id, start, end)

    stmt = (
        select(MedicationLog)
        .where(MedicationLog.member_id == member_id)
        .where(MedicationLog.scheduled_date >= start)
        .where(MedicationLog.scheduled_date <= end)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    by_date: dict[date, list[MedicationLog]] = {}
    for log in logs:
        by_date.setdefault(log.scheduled_date, []).append(log)

    days = []
    for d in range(1, last_day + 1):
        cur = date(year, month, d)
        day_logs = by_date.get(cur, [])
        scheduled = len(day_logs)
        taken = sum(1 for l in day_logs if l.status == "taken")
        missed = sum(1 for l in day_logs if l.status == "missed")
        skipped = sum(1 for l in day_logs if l.status == "skipped")
        status = "none"
        if scheduled:
            if taken == scheduled:
                status = "complete"
            elif missed > 0:
                status = "missed" if (missed + skipped) == scheduled else "partial"
            elif skipped == scheduled:
                status = "skipped"
            else:
                status = "partial"
        days.append(MedicationCalendarDay(
            date=cur, scheduled_count=scheduled, taken_count=taken, missed_count=missed, skipped_count=skipped, status=status
        ))

    return ResponseWrapper(data=MedicationCalendarOut(year=year, month=month, days=days))
```

- [ ] **Step 4：写集成测试**

```python
@pytest.mark.asyncio
async def test_medication_calendar(auth_client, test_member, db):
    from app.models.medication import Medication, MedicationLog
    med = Medication(member_id=test_member.id, name="阿司匹林", dosage="100mg", frequency="daily", time_slots=["08:00"], start_date=date.today(), status="active")
    db.add(med); await db.flush()
    db.add(MedicationLog(medication_id=med.id, member_id=test_member.id, scheduled_date=date.today(), scheduled_time="08:00", status="taken"))
    await db.commit()
    ym = date.today().strftime("%Y-%m")
    resp = await auth_client.get(f"/api/medications/calendar?member_id={test_member.id}&year_month={ym}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["year"] == date.today().year
```

- [ ] **Step 5：运行测试并提交**

Run: `pytest tests/integration/test_medications.py -v`
Expected: PASS

Commit: `feat(medication): add medication calendar API`

### Task 4.2：漏服检测与提醒自动生成

**Files:**
- Create: `backend/app/core/reminder_engine.py`
- Create: `backend/app/services/reminder_service.py`（可选，若逻辑简单可合并入 engine）
- Modify: `backend/app/tasks/cron.py`
- Modify: `backend/app/celery_app.py`（注册 beat schedule）
- Test: `backend/tests/unit/test_reminder_engine.py`

**Interfaces:**
- Consumes: `AsyncSession`, current date
- Produces: created/updated `Reminder` records, updated `MedicationLog` / `VaccineRecord` status

- [ ] **Step 1：实现漏服检测引擎**

```python
from datetime import date, datetime, timezone
from sqlalchemy import select
from app.models.medication import Medication, MedicationLog
from app.models.reminder import Reminder

class ReminderEngine:
    @staticmethod
    async def scan_missed_medications(db, today: date | None = None):
        today = today or date.today()
        stmt = (
            select(MedicationLog)
            .join(Medication)
            .where(Medication.status == "active")
            .where(MedicationLog.scheduled_date < today)
            .where(MedicationLog.status == "pending")
        )
        result = await db.execute(stmt)
        logs = result.scalars().all()
        for log in logs:
            log.status = "missed"
            db.add(Reminder(
                member_id=log.member_id,
                type="medication",
                title=f"漏服提醒：{log.medication.name}",
                description=f"{log.scheduled_date} {log.scheduled_time} 的剂量未打卡",
                scheduled_date=today,
                status="pending",
                priority="high",
            ))
        await db.commit()
        return len(logs)
```

- [ ] **Step 2：实现疫苗逾期扫描**

```python
from app.models.vaccine import VaccineRecord

@staticmethod
async def scan_overdue_vaccines(db, today: date | None = None):
    today = today or date.today()
    stmt = (
        select(VaccineRecord)
        .where(VaccineRecord.status.in_(["pending", "upcoming"]))
        .where(VaccineRecord.scheduled_date < today)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()
    for rec in records:
        rec.status = "overdue"
        db.add(Reminder(
            member_id=rec.member_id,
            type="vaccine",
            title=f"疫苗逾期：{rec.vaccine_name} 第{rec.dose}针",
            description=f"原定于 {rec.scheduled_date} 接种，已逾期",
            scheduled_date=today,
            status="pending",
            priority="high",
        ))
    await db.commit()
    return len(records)
```

- [ ] **Step 3：实现提醒逾期扫描**

```python
@staticmethod
async def scan_overdue_reminders(db, today: date | None = None):
    today = today or date.today()
    stmt = (
        select(Reminder)
        .where(Reminder.status == "pending")
        .where(Reminder.scheduled_date < today)
    )
    result = await db.execute(stmt)
    reminders = result.scalars().all()
    for r in reminders:
        r.status = "overdue"
    await db.commit()
    return len(reminders)
```

- [ ] **Step 4：注册 Celery 定时任务**

```python
# app/celery_app.py
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "generate-medication-logs": {
        "task": "care_assist.generate_medication_logs",
        "schedule": crontab(hour=0, minute=5),  # 每天 00:05 生成未来 7 天日志
    },
    "scan-missed-medications": {
        "task": "care_assist.scan_missed_medications",
        "schedule": int(os.getenv("CELERY_SCAN_INTERVAL_SEC", "3600")),  # 默认 1 小时
    },
    "scan-overdue-vaccines": {
        "task": "care_assist.scan_overdue_vaccines",
        "schedule": int(os.getenv("CELERY_SCAN_INTERVAL_SEC", "3600")),
    },
    "scan-overdue-reminders": {
        "task": "care_assist.scan_overdue_reminders",
        "schedule": int(os.getenv("CELERY_SCAN_INTERVAL_SEC", "3600")),
    },
}
```

> 开发阶段可将 `CELERY_SCAN_INTERVAL_SEC=300` 设为 5 分钟以便快速验证。

- [ ] **Step 5：实现任务函数**

```python
# app/tasks/cron.py
from app.db.session import async_session
from app.core.reminder_engine import ReminderEngine
from app.tasks.utils import run_async_task

@celery_app.task(name="care_assist.scan_overdue_reminders")
def scan_overdue_reminders() -> dict:
    async def _run():
        async with async_session() as db:
            return await ReminderEngine.scan_overdue_reminders(db)
    count = run_async_task(_run())
    return {"scanned": count, "updated": count}

@celery_app.task(name="care_assist.scan_missed_medications")
def scan_missed_medications() -> dict:
    async def _run():
        async with async_session() as db:
            return await ReminderEngine.scan_missed_medications(db)
    count = run_async_task(_run())
    return {"scanned": count, "missed": count}

@celery_app.task(name="care_assist.scan_overdue_vaccines")
def scan_overdue_vaccines() -> dict:
    async def _run():
        async with async_session() as db:
            return await ReminderEngine.scan_overdue_vaccines(db)
    count = run_async_task(_run())
    return {"scanned": count, "overdue": count}
```

- [ ] **Step 6：写测试**

```python
@pytest.mark.asyncio
async def test_scan_missed_medications(db, test_member):
    from app.models.medication import Medication, MedicationLog
    med = Medication(member_id=test_member.id, name="测试药", dosage="1片", frequency="daily", time_slots=["08:00"], start_date=date(2020,1,1), status="active")
    db.add(med); await db.flush()
    log = MedicationLog(medication_id=med.id, member_id=test_member.id, scheduled_date=date(2020,1,1), scheduled_time="08:00", status="pending")
    db.add(log); await db.commit()

    from app.core.reminder_engine import ReminderEngine
    count = await ReminderEngine.scan_missed_medications(db, today=date(2020,1,2))
    assert count == 1
    assert log.status == "missed"
```

- [ ] **Step 7：运行测试并提交**

Run: `pytest tests/unit/test_reminder_engine.py tests/unit/test_celery_tasks.py -v`
Expected: PASS

Commit: `feat(reminder): add medication miss and overdue scan engine`

### Task 4.3：用药日历前端组件

**Files:**
- Create: `miniprogram/components/medication-calendar/medication-calendar.js`
- Create: `miniprogram/components/medication-calendar/medication-calendar.wxml`
- Create: `miniprogram/components/medication-calendar/medication-calendar.wxss`
- Modify: `miniprogram/pkg-medication/pages/medication/medication.js`
- Modify: `miniprogram/utils/api.js`

**Interfaces:**
- Consumes: `memberId`, `yearMonth`
- Produces: `daytap` event with `{ date }`

- [ ] **Step 1：API 封装**

在 `miniprogram/utils/api.js` 的导出对象中新增方法（不要覆盖已有导出）：

```javascript
module.exports = {
  get(url) { return request({ url, method: 'GET' }) },
  post(url, data) { return request({ url, method: 'POST', data }) },
  put(url, data) { return request({ url, method: 'PUT', data }) },
  del(url) { return request({ url, method: 'DELETE' }) },
  uploadFile,
  getMedicationCalendar(memberId, yearMonth) {
    return request({ url: `/api/medications/calendar?member_id=${memberId}&year_month=${yearMonth}`, method: 'GET' })
  },
}
```

- [ ] **Step 2：组件实现（节选）**

```javascript
Component({
  properties: { memberId: String, yearMonth: String },
  data: { days: [], weekdays: ['日','一','二','三','四','五','六'] },
  lifetimes: {
    attached() { this.load() }
  },
  observers: {
    'yearMonth,memberId': function() { this.load() }
  },
  methods: {
    async load() {
      if (!this.data.yearMonth || !this.data.memberId) return
      const res = await getMedicationCalendar(this.data.memberId, this.data.yearMonth)
      this.setData({ days: res.data.days })
    },
    onDayTap(e) {
      this.triggerEvent('daytap', { date: e.currentTarget.dataset.date })
    }
  }
})
```

- [ ] **Step 3：提交**

Commit: `feat(ui): add medication calendar component`

---

## Phase 5：疫苗子系统（P1-6）

### Task 5.1：标准疫苗库排期与逾期 API

**Files:**
- Modify: `backend/app/api/vaccines.py`
- Modify: `backend/app/schemas/vaccine.py`
- Modify: `backend/app/db/seed.py`（接种时自动调用）
- Modify: `backend/app/api/members.py`（新增成员时可选初始化疫苗计划）
- Test: `backend/tests/integration/test_vaccines.py`

**Interfaces:**
- Consumes: `member_id`, child's `birth_date`
- Produces: `VaccineScheduleOut` with generated records and overdue flags

- [ ] **Step 1：新增 Schema**

```python
class VaccineScheduleOut(BaseModel):
    records: list[VaccineRecordOut]
    overdue_count: int
    upcoming_count: int
```

- [ ] **Step 2：新增排期服务函数**

```python
from datetime import date
from app.models.vaccine_library import VaccineLibrary
from app.models.vaccine import VaccineRecord
from sqlalchemy import select

async def generate_vaccine_schedule(db, member) -> list[VaccineRecord]:
    if not member.birth_date:
        return []

    lib = await db.execute(select(VaccineLibrary).order_by(VaccineLibrary.recommended_age_months))
    entries = lib.scalars().all()

    # Idempotent: skip doses that already exist for this member
    existing_stmt = select(VaccineRecord.vaccine_name, VaccineRecord.dose).where(VaccineRecord.member_id == member.id)
    existing_result = await db.execute(existing_stmt)
    existing_keys = {(r.vaccine_name, r.dose) for r in existing_result.all()}

    records = []
    today = date.today()
    for entry in entries:
        if (entry.name, entry.dose_number) in existing_keys:
            continue
        scheduled = add_months(member.birth_date, entry.recommended_age_months)
        if scheduled < today:
            status = "overdue"
        elif scheduled > today:
            status = "upcoming"
        else:
            status = "pending"
        records.append(VaccineRecord(
            member_id=member.id,
            vaccine_name=entry.name,
            dose=entry.dose_number,
            scheduled_date=scheduled,
            status=status,
            is_custom=False,
        ))
    if records:
        db.add_all(records)
        await db.commit()
    return records

def add_months(d: date, months: int) -> date:
    year = d.year + (d.month + months - 1) // 12
    month = (d.month + months - 1) % 12 + 1
    day = min(d.day, [31,29 if (year % 4 == 0 and year % 100 != 0) or year % 400 == 0 else 28,31,30,31,30,31,31,30,31,30,31][month-1])
    return date(year, month, day)
```

- [ ] **Step 3：新增 API endpoint**

```python
@router.post("/schedule", response_model=ResponseWrapper[VaccineScheduleOut])
async def generate_schedule(
    member_id: str = Query(...),
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    target = await _verify_member_in_family(member_id, current, db)
    records = await generate_vaccine_schedule(db, target)
    overdue = sum(1 for r in records if r.status == "overdue")
    upcoming = sum(1 for r in records if r.status == "upcoming")
    return ResponseWrapper(data=VaccineScheduleOut(
        records=[VaccineRecordOut.model_validate(r) for r in records],
        overdue_count=overdue,
        upcoming_count=upcoming,
    ))
```

- [ ] **Step 4：写测试**

```python
@pytest.mark.asyncio
async def test_generate_vaccine_schedule(auth_client, test_member, db):
    from app.models.vaccine_library import VaccineLibrary
    db.add(VaccineLibrary(name="测试疫苗", dose_number=1, recommended_age_months=0, category="测试"))
    await db.commit()
    test_member.birth_date = date(2020,1,1)
    await db.commit()
    resp = await auth_client.post(f"/api/vaccines/schedule?member_id={test_member.id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["records"]) >= 1
```

- [ ] **Step 5：运行测试并提交**

Run: `pytest tests/integration/test_vaccines.py -v`
Expected: PASS

Commit: `feat(vaccine): add standard vaccine schedule generation and overdue calc`

---

## Phase 6：报告子系统（P1-7 一键提醒）

### Task 6.1：报告一键生成提醒 API

**Files:**
- Create: `backend/app/services/reminder_service.py`（若无）
- Modify: `backend/app/api/reminders.py`
- Modify: `backend/app/schemas/reminder.py`
- Modify: `backend/app/api/reports.py`（在 OCR 完成后可选自动创建提醒）
- Test: `backend/tests/integration/test_reminders.py`

**Interfaces:**
- Consumes: `member_id`, `report_id`, `reminder_type`, `scheduled_date`
- Produces: `ReminderOut`

- [ ] **Step 1：新增服务函数**

```python
from app.models.report import Report
from app.models.reminder import Reminder

async def create_reminder_from_report(db, report: Report, scheduled_date: date) -> Reminder:
    summary = report.ai_summary or f"{report.type}报告"
    reminder = Reminder(
        member_id=report.member_id,
        type="review",
        title=f"复查提醒：{summary[:30]}",
        description=f"基于报告 {report.id} 生成的复查提醒",
        scheduled_date=scheduled_date,
        status="pending",
        related_report_id=report.id,
        priority="normal",
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return reminder
```

- [ ] **Step 2：新增 API endpoint**

```python
class ReminderGenerateRequest(BaseModel):
    member_id: str
    report_id: str
    scheduled_date: date

@router.post("/from-report", response_model=ResponseWrapper[ReminderOut])
async def create_from_report(
    payload: ReminderGenerateRequest,
    current: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    target = await _verify_member_in_family(payload.member_id, current, db)
    report = await db.get(Report, payload.report_id)
    if not report or report.member_id != target.id:
        raise NotFoundException("报告不存在")
    from app.services.reminder_service import create_reminder_from_report
    reminder = await create_reminder_from_report(db, report, payload.scheduled_date)
    return ResponseWrapper(data=ReminderOut.model_validate(reminder))
```

- [ ] **Step 3：在报告 OCR 完成后自动创建异常指标提醒（可选）**

```python
# 在 reports.py trigger_ocr 末尾
for item in all_extracted:
    if item.get("status") in ("high", "critical"):
        db.add(Reminder(
            member_id=report.member_id,
            type="checkup",
            title=f"指标异常复查：{item['indicator_name']}",
            description=f"报告 OCR 识别到 {item['indicator_name']} 为 {item['status']}，建议复查",
            scheduled_date=(report.report_date or date.today()) + timedelta(days=7),
            status="pending",
            related_report_id=report.id,
            related_indicator=item["indicator_key"],
            priority="high",
        ))
await db.commit()
```

- [ ] **Step 4：写测试**

```python
@pytest.mark.asyncio
async def test_create_reminder_from_report(auth_client, test_creator, db):
    from app.models.report import Report
    report = Report(member_id=test_creator.id, type="lab", ocr_status="pending")
    db.add(report); await db.commit()
    payload = {"member_id": test_creator.id, "report_id": report.id, "scheduled_date": str(date.today())}
    resp = await auth_client.post("/api/reminders/from-report", json=payload)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["related_report_id"] == report.id
```

- [ ] **Step 5：运行测试并提交**

Run: `pytest tests/integration/test_reminders.py -v`
Expected: PASS

Commit: `feat(report): add one-click reminder from report`

---

## 前端集成清单

| 能力 | 组件/页面 | 依赖后端 API | 关键改动 |
|------|-----------|--------------|----------|
| 全局 AI 悬浮球 | `components/ai-fab` | `/api/ai-conversations` | `app.json` usingComponents；每个 page 引入 |
| 动态快捷问题 | `components/ai-quick-questions` | `/api/ai-conversations/quick-questions` | AI 页打开时拉取 |
| 趋势图 Bottom Sheet | `components/trend-bottom-sheet` | `/api/indicators/compare` | 指标页长按/多选触发 |
| 用药日历 | `components/medication-calendar` | `/api/medications/calendar` | 用药详情页顶部 |
| 漏服/逾期提醒 | 无新组件 | Celery 任务（Task 4.0 预生成日志 + Task 4.2 扫描） | 提醒列表页自动展示 |
| 标准疫苗库 | `pkg-child/pages/vaccine` | `/api/vaccines/schedule` | 儿童页增加“生成接种计划”按钮 |
| 报告 AI 摘要 | `pkg-system/pages/report-detail` | `/api/reports/{id}/ai-summary` | 报告详情页增加摘要卡片 |
| 报告一键提醒 | `pkg-system/pages/report-detail` | `/api/reminders/from-report` | 报告详情页增加“添加复查提醒”按钮 |

---

## 开发节奏

建议按以下节奏分 4 个迭代交付，每个迭代结束时前后端联调并跑通相关测试。

### 迭代 1：基础设施（约 2-3 天）

- Task 1.1 Celery 框架
- Task 1.2 提醒规则模型（P1 跳过）
- Task 1.3 标准疫苗库模型与种子
- Task 4.0 用药计划日志预生成

**验收标准：**
- `pytest tests/unit/test_celery_tasks.py tests/unit/test_vaccine_library.py tests/unit/test_medication_log_service.py` 全部通过
- `alembic upgrade head` 成功应用所有新迁移

### 迭代 2：AI 体验（约 3-4 天）

- Task 2.1 全局 AI 悬浮球
- Task 2.2 动态快捷问题
- Task 2.3 报告 AI 摘要

**验收标准：**
- 小程序每个 Tab 页可见 AI 悬浮球，点击跳转 AI 页
- AI 页根据进入来源展示不同快捷问题
- 报告详情页可生成 AI 摘要

### 迭代 3：指标与用药（约 4-5 天）

- Task 3.1 多指标对比 API
- Task 3.2 趋势图 Bottom Sheet
- Task 4.1 用药日历 API
- Task 4.2 漏服/逾期扫描引擎
- Task 4.3 用药日历组件

**验收标准：**
- 指标页支持选择 2-4 个指标对比趋势
- 用药页展示日历，标记完成/漏服
- 模拟漏服后运行 Celery 任务可生成提醒

### 迭代 4：疫苗与报告提醒（约 3-4 天）

- Task 5.1 标准疫苗库排期与逾期
- Task 6.1 报告一键提醒
- 补充前端疫苗页与报告详情页

**验收标准：**
- 新增儿童成员后可生成标准疫苗计划
- 疫苗逾期自动更新状态并生成提醒
- 报告页可一键添加复查提醒

### 回归与发布前检查

- 全量测试：`cd backend && pytest`
- 代码检查：`ruff check . && mypy .`
- 小程序真机或开发者工具 smoke test：登录 → 指标 → 用药 → 疫苗 → 报告

---

## 测试策略

1. **单元测试**：每个新引擎/服务必须有独立单元测试，使用 mock 替代外部 AI/OCR。
2. **集成测试**：每个新 API endpoint 必须有 integration test，使用 `auth_client` + 真实测试数据库。
3. **定时任务测试**：在单元测试中直接调用 `ReminderEngine.scan_*` 方法，不启动 Celery worker。
4. **前端测试**：以开发者工具真机预览为主，关键组件在 `e2e/test_core_path.py` 中补充步骤。
5. **种子数据测试**：疫苗库种子幂等性必须验证，避免重复运行导致数据膨胀。

---

## 风险与依赖

- **Celery Beat 运行环境**：生产环境需要独立部署 `celery -A app.celery_app beat` 和 worker；本地开发可通过手动触发任务或周期性调接口验证。
- **AI Provider 可用性**：报告摘要/快捷问题在无 API key 时回退到规则逻辑，确保本地开发和测试不依赖外部服务。
- **小程序全局组件限制**：微信小程序不支持全局自动注入组件，需在 `app.json` 注册 `usingComponents` 后，在每个 page.wxml 底部 `<ai-fab />` 引入。可考虑构建时脚本自动生成，但当前方案保持手动添加。
- ** Canvas 趋势图复杂度**：若团队无 canvas 绘图经验，建议引入 `wx-charts` 或 `echarts-for-weixin` 分包；本方案先用原生 canvas 绘制基础折线，后续迭代美化。

---

## Spec 覆盖自检

| 需求 | 对应任务 |
|------|----------|
| 全局 AI 悬浮球 | Task 2.1 |
| 动态 AI 快捷问题 | Task 2.2 |
| 趋势图 Bottom Sheet / 多指标对比 | Task 3.1, Task 3.2 |
| 用药打卡日历与漏服提醒 | Task 4.1, Task 4.2, Task 4.3 |
| 提醒系统自动触发 | Task 1.1, Task 4.0, Task 4.2 |
| 标准疫苗库与逾期计算 | Task 1.3, Task 5.1 |
| 报告 AI 摘要与一键提醒 | Task 2.3, Task 6.1 |

无占位符（TBD/待实现/类似 Task X）。所有新增接口、模型、schema、文件路径均已明确。
