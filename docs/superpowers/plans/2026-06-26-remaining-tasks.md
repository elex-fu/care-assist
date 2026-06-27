# Care Assist P0 剩余开发任务 — 优化方案

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> 生成时间：2026-06-26
> 来源计划：`docs/superpowers/plans/2026-06-25-p0-core-features.md`

**Goal:** 补全 P0 核心功能中尚未完成的指标矩阵视图、手动录入、慢性病专区、儿童成长发育、真实 OCR 五大模块，使每个模块达到可测试、可提交状态。

**Architecture:** 后端延续 FastAPI + SQLAlchemy 2.0 async + Pydantic v2 + pytest 的现有模式；前端沿用原生微信小程序分包结构。每个任务按“后端接口/模型 → 单元/集成测试 → 前端页面 → 入口集成”顺序推进，优先完成依赖链上游任务。

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0 async, Alembic, pytest, Pydantic v2; 微信小程序原生 WXML/WXSS/JS; Redis + Celery（仅开发环境使用）。

---

## 全局约束

- Python >=3.11, FastAPI >=0.110, SQLAlchemy 2.0 async, MySQL 8.0+（开发端口 `3308`）。
- 前端：原生微信小程序，不使用第三方框架；新增页面必须在 `app.json` 对应分包 `pages` 数组中注册。
- 测试：pytest + pytest-asyncio，TDD 风格；新增后端代码必须带对应单元/集成测试。
- 代码风格：ruff line-length 100，mypy strict。
- 提交格式：`feat(scope): description`，结尾加 `Co-Authored-By: Claude <noreply@anthropic.com>`。
- API key / 敏感信息只走 `.env`，不提交 git。
- 新增 API 必须在 `backend/app/main.py` 注册。
- 新增数据模型必须通过 Alembic 生成迁移。
- 不要 `git add -A` 误提交 `.mysql_data/`、`uploads/`、`e2e/screenshots/` 等 untracked 目录。

---

## 当前状态总览

| 任务 | 完成度 | 现状 | 阻塞/依赖 |
|------|--------|------|-----------|
| **Task 2: P0-3 指标中心表单视图** | ~70% | 后端 `/matrix` 端点、Schema、测试已落地；前端 WXML 已写但 JS/WXSS 缺失，视图无法交互。 | 无阻塞，可直接收尾。 |
| **Task 3: P0-6 手动录入页** | ~10% | `indicator_engine.py` 里已有 `THRESHOLDS`/`NAME_MAPPING`/`standardize()`；无专门搜索 API 与手动录入页面。 | 依赖 Task 2 完成后可并行（元数据概念）。 |
| **Task 4: P0-4 慢性病专区** | ~5% | `Member.chronic_diseases` JSON 字段已存在；无套餐定义、无 API、无页面。 | 依赖 Task 3 的指标标准化/搜索能力。 |
| **Task 5: P0-5 儿童成长与发育** | ~15% | `pkg-child` 分包、疫苗页面、儿童 dashboard 已存在；无 `GrowthRecord` 模型、无生长曲线、无里程碑。 | 可独立并行，与 Task 2-4 几乎无耦合。 |
| **Task 6: P0-2 真实 OCR 报告识别** | ~30% | OCR 流水线接口 `POST /api/reports/{id}/ocr` 与 mock/regex 服务已存在；无真实云 OCR Provider、无配置。 | 依赖 Task 3 的 `indicator_normalizer` 做指标名标准化。 |

---

## 文件结构总览

```
# Task 2 收尾
miniprogram/pages/indicators/indicators.js       # 新增 viewMode / loadMatrix / switchViewMode / onMatrixCellTap
miniprogram/pages/indicators/indicators.wxss     # 新增 matrix 系列样式
backend/app/api/indicators.py                    # GET /matrix 已存在，需验证
backend/tests/unit/test_indicator_matrix.py      # 已存在，需确认 pytest 可收集
backend/tests/integration/test_indicator_matrix_api.py  # 已存在，需跑通

# Task 3 手动录入
backend/app/schemas/indicator_metadata.py        # 新增 IndicatorMetadata
backend/app/core/indicator_search.py             # 新增：基于 indicator_engine 的搜索/补全
backend/app/api/indicators.py                    # 新增 GET /api/indicators/metadata
backend/tests/unit/test_indicator_search.py      # 新增
backend/tests/integration/test_indicator_metadata.py  # 新增
miniprogram/pkg-system/pages/indicator-manual/indicator-manual.{js,wxml,json,wxss}  # 新增页面
miniprogram/pages/upload/upload.{js,wxml}        # OCR 失败时增加手动录入入口
miniprogram/app.json                             # pkg-system 注册新页面

# Task 4 慢性病专区
backend/app/core/chronic_packages.py             # 新增套餐定义
backend/app/schemas/chronic.py                   # 新增 ChronicPackageResponse / ChronicIndicatorItem
backend/app/api/indicators.py                    # 新增 /api/indicators/chronic, /api/indicators/chronic/{package}
backend/tests/unit/test_chronic_packages.py      # 新增
backend/tests/integration/test_chronic.py        # 新增
miniprogram/pkg-system/pages/chronic/chronic.{js,wxml,json,wxss}  # 新增页面
miniprogram/pages/profile/profile.{js,wxml}      # 增加入口
miniprogram/app.json                             # pkg-system 注册新页面

# Task 5 儿童成长与发育
backend/app/models/growth_record.py              # 新增 GrowthRecord 模型
backend/app/models/member.py                     # 增加 growth_records relationship
backend/app/schemas/growth.py                    # 新增 GrowthRecordCreate / GrowthRecordOut / MilestoneItem
backend/app/core/milestone_data.py               # 新增里程碑静态数据
backend/app/api/child.py                         # 新增 router：成长 CRUD + milestones
backend/app/main.py                              # 注册 child router
backend/alembic/versions/xxxx_add_growth_records_table.py  # 新增迁移
backend/tests/unit/test_milestone_data.py        # 新增
backend/tests/integration/test_child_growth.py   # 新增
miniprogram/pkg-child/pages/growth/growth.{js,wxml,json,wxss}      # 新增
miniprogram/pkg-child/pages/milestone/milestone.{js,wxml,json,wxss}  # 新增
miniprogram/pkg-child/pages/child-dashboard/child-dashboard.{js,wxml}  # 增加入口
miniprogram/app.json                             # pkg-child 注册新页面

# Task 6 真实 OCR
backend/app/ai/ocr_provider.py                   # 新增 OCRProvider 抽象
backend/app/ai/baidu_ocr_provider.py             # 新增百度云 OCR 实现
backend/app/ai/tencent_ocr_provider.py           # 新增腾讯云 OCR（占位）
backend/app/ai/factory.py                        # 新增 get_ocr_provider / ocr_with_fallback
backend/app/config.py                            # 新增 OCR Provider 配置项
backend/app/services/ocr_pipeline.py             # 新增 OCR 流水线 + 指标解析
backend/app/schemas/ocr.py                       # 新增 OCR 响应 Schema
backend/app/core/ocr_service.py                  # 保留 mock/regex fallback
backend/app/api/reports.py                       # POST /reports/{id}/ocr 接入 pipeline
backend/.env.example                             # 新增 OCR 配置示例
backend/tests/unit/test_ocr_pipeline.py          # 新增
backend/tests/integration/test_ocr_real.py       # 新增
```

---

## 推荐开发方式

采用 **Subagent-Driven Development（推荐）**：

- 每个子任务（Step）拆分为一次独立 subagent 执行。
- Subagent 只拿到当前子任务的上下文，避免上下文污染。
- 每个子任务输出：代码改动 + 测试通过截图/命令输出 + commit。
- 主会话在每个子任务结束后做快速 review，再派发下一个子任务。
- 遇到阻塞立即暂停，由主会话分析并调整计划。

替代方案：

- **Inline Execution**：在同一个会话中顺序执行所有 step，适合改动范围极小（如仅 Task 2 收尾）。
- 若选择 inline，使用 `superpowers:executing-plans`。

---

## 任务拆分与执行顺序

### Phase 1: 立即收尾（无外部依赖）

#### Task 2.1: 验证后端矩阵测试

**目标：** 确认 `/api/indicators/matrix` 后端实现及测试可被 pytest 正确收集并跑通。

**Files:**
- Read: `backend/app/schemas/indicator_matrix.py`
- Read: `backend/app/api/indicators.py:231-286`
- Read: `backend/tests/unit/test_indicator_matrix.py`
- Read: `backend/tests/integration/test_indicator_matrix_api.py`
- Verify: `backend/app/main.py` 中 indicators router 注册

**Steps:**

- [ ] **Step 1: 检查 pytest 收集情况**

```bash
cd /Users/lex/play/care-assist/backend
source .venv/bin/activate
python -m pytest tests/unit/test_indicator_matrix.py tests/integration/test_indicator_matrix_api.py -v --collect-only -p no:cacheprovider
```

预期：至少收集到 `test_matrix_cell_schema`、`test_matrix_response_schema`、集成测试 3-4 条。

- [ ] **Step 2: 运行测试**

```bash
python -m pytest tests/unit/test_indicator_matrix.py tests/integration/test_indicator_matrix_api.py -v -p no:cacheprovider
```

预期：全部 PASS。若有 FAIL，记录并修复。

- [ ] **Step 3: 若测试为空，定位原因**

常见原因：
- 函数名不以 `test_` 开头。
- 文件不在 `tests/` 目录或被 `pytest.ini` 忽略。
- 使用了 `unittest.TestCase` 但无 `test_*` 方法。

修复后重新运行 Step 2。

- [ ] **Step 4: Commit（如测试已可运行）**

```bash
git add tests/unit/test_indicator_matrix.py tests/integration/test_indicator_matrix_api.py
# 仅当真有改动时才 commit
git diff --cached --quiet || git commit -m "test(matrix): ensure indicator matrix tests are collectable and passing

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

#### Task 2.2: 实现前端矩阵交互 JS

**目标：** 让 `indicators.js` 支持视图切换、加载矩阵数据、点击单元格查看详情。

**Files:**
- Modify: `miniprogram/pages/indicators/indicators.js`
- Read: `miniprogram/pages/indicators/indicators.wxml:48-94`
- Read: `miniprogram/utils/api.js`（确认 `api.get` 用法）

**Interfaces:**
- Consumes: `GET /api/indicators/matrix?member_id={id}&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` → `IndicatorMatrixResponse`
- Produces: `data.viewMode`, `data.matrix`, `switchViewMode(e)`, `loadMatrix()`, `onMatrixCellTap(e)`

**Steps:**

- [ ] **Step 1: 在 `data` 中新增矩阵状态**

```javascript
data: {
  // ... 现有字段保留
  viewMode: 'list', // 'list' | 'matrix'
  matrix: null,     // IndicatorMatrixResponse 或 null
  matrixLoading: false,
}
```

- [ ] **Step 2: 实现 `switchViewMode(e)`**

```javascript
switchViewMode(e) {
  const mode = e.currentTarget.dataset.mode || e.detail.value;
  this.setData({ viewMode: mode });
  if (mode === 'matrix' && !this.data.matrix) {
    this.loadMatrix();
  }
},
```

- [ ] **Step 3: 实现 `loadMatrix()`**

```javascript
async loadMatrix() {
  const { activeMemberId } = this.data;
  if (!activeMemberId) return;
  this.setData({ matrixLoading: true });
  try {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 29);
    const fmt = (d) => d.toISOString().split('T')[0];
    const res = await api.get('/indicators/matrix', {
      member_id: activeMemberId,
      start_date: fmt(start),
      end_date: fmt(end),
    });
    this.setData({ matrix: res.data || res });
  } catch (err) {
    console.error('loadMatrix failed', err);
    wx.showToast({ title: '加载矩阵失败', icon: 'none' });
  } finally {
    this.setData({ matrixLoading: false });
  }
},
```

注意：`api.get` 的返回值格式以 `api.js` 实际实现为准（可能是 `res.data` 或已被 unwrap 的 `res`）。

- [ ] **Step 4: 实现 `onMatrixCellTap(e)`**

```javascript
onMatrixCellTap(e) {
  const { date, indicatorKey, value, status } = e.currentTarget.dataset;
  if (value === undefined || value === null || value === '') return;
  wx.showModal({
    title: `${date} ${indicatorKey}`,
    content: `数值：${value}\n状态：${status || '正常'}`,
    showCancel: false,
  });
},
```

- [ ] **Step 5: 在 `onLoad` / 切换成员后自动加载矩阵**

若当前 `viewMode === 'matrix'` 且 `activeMemberId` 变化，调用 `loadMatrix()`。

- [ ] **Step 6: 运行小程序开发者工具预览**

切换到“矩阵”视图，确认网络请求成功、数据渲染、点击弹窗正常。

- [ ] **Step 7: Commit**

```bash
git add miniprogram/pages/indicators/indicators.js
git commit -m "feat(frontend): indicator matrix view interactions

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

#### Task 2.3: 实现前端矩阵样式 WXSS

**目标：** 给矩阵视图添加滚动、单元格状态色、切换按钮样式。

**Files:**
- Modify: `miniprogram/pages/indicators/indicators.wxss`
- Read: `miniprogram/pages/indicators/indicators.wxml:48-94`

**Interfaces:**
- Consumes: WXML 中已有的 class 名 `.view-toggle`, `.matrix-scroll`, `.matrix-table`, `.matrix-header`, `.matrix-row`, `.matrix-cell`, `.matrix-date`, `.status-normal`, `.status-low`, `.status-high`, `.status-critical`, `.empty-state`

**Steps:**

- [ ] **Step 1: 编写切换按钮样式**

```css
.view-toggle {
  display: flex;
  justify-content: center;
  padding: 24rpx 0;
}
.view-toggle .toggle-item {
  padding: 12rpx 32rpx;
  margin: 0 8rpx;
  border: 1rpx solid #e0e0e0;
  border-radius: 32rpx;
  font-size: 28rpx;
  color: #666;
  background: #fff;
}
.view-toggle .toggle-item.active {
  color: #fff;
  background: #07c160;
  border-color: #07c160;
}
```

- [ ] **Step 2: 编写矩阵表格容器样式**

```css
.matrix-scroll {
  width: 100%;
  white-space: nowrap;
}
.matrix-table {
  display: inline-table;
  border-collapse: collapse;
  min-width: 100%;
}
.matrix-row {
  display: table-row;
}
.matrix-header .matrix-cell {
  background: #f7f7f7;
  font-weight: 500;
  color: #333;
}
.matrix-cell {
  display: table-cell;
  min-width: 120rpx;
  padding: 20rpx 16rpx;
  text-align: center;
  font-size: 26rpx;
  border: 1rpx solid #eee;
  vertical-align: middle;
}
.matrix-date {
  background: #fafafa;
  color: #666;
  font-size: 24rpx;
}
```

- [ ] **Step 3: 编写状态色**

```css
.status-normal { color: #07c160; }
.status-low { color: #ffbe00; }
.status-high { color: #ffbe00; }
.status-critical { color: #fa5151; font-weight: 600; }
```

- [ ] **Step 4: 空状态样式**

```css
.empty-state {
  text-align: center;
  padding: 80rpx 40rpx;
  color: #999;
  font-size: 28rpx;
}
```

- [ ] **Step 5: 预览并微调**

在微信开发者工具中切换 list/matrix 视图，检查横向滚动、列对齐、状态色。

- [ ] **Step 6: Commit**

```bash
git add miniprogram/pages/indicators/indicators.wxss
git commit -m "feat(frontend): indicator matrix view styles

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Phase 2: 手动录入（依赖 Task 2 完成后启动）

#### Task 3.1: 后端指标搜索 API

**目标：** 提供 `GET /api/indicators/metadata?q={query}`，返回指标名、单位、参考范围、别名。

**Files:**
- Create: `backend/app/schemas/indicator_metadata.py`
- Create: `backend/app/core/indicator_search.py`
- Modify: `backend/app/api/indicators.py`
- Create: `backend/tests/unit/test_indicator_search.py`
- Create: `backend/tests/integration/test_indicator_metadata.py`

**Interfaces:**
- Consumes: `indicator_engine.THRESHOLDS`, `indicator_engine.NAME_MAPPING`
- Produces:
  - `GET /api/indicators/metadata?q={query}` → `list[IndicatorMetadata]`
  - `indicator_search.search_indicators(query: str, limit: int = 10) -> list[IndicatorMetadata]`

**IndicatorMetadata Schema:**

```python
class IndicatorMetadata(BaseModel):
    key: str
    name: str
    aliases: list[str]
    unit: str
    ref_range: str | None
```

**Steps:**

- [ ] **Step 1: 写集成测试（先失败）**

```python
# backend/tests/integration/test_indicator_metadata.py
import pytest

@pytest.mark.asyncio
async def test_search_indicator_metadata(auth_client, test_member):
    res = await auth_client.get("/indicators/metadata?q=血压")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert any(item["key"] in ("systolic_bp", "diastolic_bp") for item in data)

@pytest.mark.asyncio
async def test_search_indicator_metadata_empty(auth_client, test_member):
    res = await auth_client.get("/indicators/metadata?q=不存在的指标")
    assert res.status_code == 200
    assert res.json() == []
```

- [ ] **Step 2: 写 Schema**

```python
# backend/app/schemas/indicator_metadata.py
from pydantic import BaseModel

class IndicatorMetadata(BaseModel):
    key: str
    name: str
    aliases: list[str]
    unit: str
    ref_range: str | None
```

- [ ] **Step 3: 实现搜索模块**

```python
# backend/app/core/indicator_search.py
from app.schemas.indicator_metadata import IndicatorMetadata
from app.core.indicator_engine import THRESHOLDS, NAME_MAPPING

# 从 THRESHOLDS 提取 unit 与 ref_range
...

def search_indicators(query: str, limit: int = 10) -> list[IndicatorMetadata]:
    q = query.strip().lower()
    results = []
    for key, meta in _METADATA.items():
        if q in key.lower() or q in meta.name.lower() or any(q in a.lower() for a in meta.aliases):
            results.append(meta)
        if len(results) >= limit:
            break
    return results
```

- [ ] **Step 4: 在 indicators router 注册 API**

```python
# backend/app/api/indicators.py
from app.core.indicator_search import search_indicators
from app.schemas.indicator_metadata import IndicatorMetadata

@router.get("/metadata", response_model=list[IndicatorMetadata])
async def get_indicator_metadata(
    q: str = "",
    current_member: Member = Depends(get_current_member),
):
    return search_indicators(q)
```

- [ ] **Step 5: 运行单元 + 集成测试**

```bash
python -m pytest tests/unit/test_indicator_search.py tests/integration/test_indicator_metadata.py -v
```

预期：全部 PASS。

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/indicator_metadata.py backend/app/core/indicator_search.py backend/app/api/indicators.py backend/tests/unit/test_indicator_search.py backend/tests/integration/test_indicator_metadata.py
git commit -m "feat(backend): indicator metadata search API

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

#### Task 3.2: 前端手动录入页面

**目标：** 创建 `indicator-manual` 页面，支持搜索指标、自动带出单位与参考范围、输入数值并保存。

**Files:**
- Create: `miniprogram/pkg-system/pages/indicator-manual/indicator-manual.json`
- Create: `miniprogram/pkg-system/pages/indicator-manual/indicator-manual.wxml`
- Create: `miniprogram/pkg-system/pages/indicator-manual/indicator-manual.wxss`
- Create: `miniprogram/pkg-system/pages/indicator-manual/indicator-manual.js`
- Modify: `miniprogram/app.json`

**Interfaces:**
- Consumes:
  - `GET /api/indicators/metadata?q={query}` → `list[IndicatorMetadata]`
  - `POST /api/indicators`（现有接口，保存 IndicatorData）
- Produces: 手动录入页面 `/pkg-system/pages/indicator-manual/indicator-manual?member_id={id}`

**Steps：**

- [ ] **Step 1: 新增页面配置**

```json
// miniprogram/pkg-system/pages/indicator-manual/indicator-manual.json
{
  "usingComponents": {},
  "navigationBarTitleText": "手动录入指标"
}
```

- [ ] **Step 2: 在 app.json 注册分包页面**

在 `pkg-system` 分包的 `pages` 数组追加 `"pages/indicator-manual/indicator-manual"`。

- [ ] **Step 3: 编写 WXML**

包含：搜索输入框、候选列表、已选指标展示（名称/单位/参考范围）、数值输入、日期选择、保存按钮。

- [ ] **Step 4: 编写 JS**

```javascript
Page({
  data: {
    memberId: null,
    query: '',
    suggestions: [],
    selected: null,
    value: '',
    recordDate: '',
  },
  onLoad(options) {
    this.setData({
      memberId: options.member_id,
      recordDate: new Date().toISOString().split('T')[0],
    });
  },
  onQueryChange(e) {
    const query = e.detail.value;
    this.setData({ query });
    this.fetchSuggestions(query);
  },
  async fetchSuggestions(query) {
    if (!query.trim()) return this.setData({ suggestions: [] });
    const res = await api.get('/indicators/metadata', { q: query });
    this.setData({ suggestions: res.data || res });
  },
  selectIndicator(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ selected: this.data.suggestions[idx], suggestions: [], query: '' });
  },
  async submit() {
    const { memberId, selected, value, recordDate } = this.data;
    await api.post('/indicators', {
      member_id: memberId,
      indicator_key: selected.key,
      value: parseFloat(value),
      unit: selected.unit,
      recorded_at: recordDate,
    });
    wx.showToast({ title: '保存成功', icon: 'success' });
    setTimeout(() => wx.navigateBack(), 1200);
  },
});
```

注意：`api.post` 的实际参数格式以 `api.js` 为准。

- [ ] **Step 5: 编写 WXSS**

搜索框、候选项、表单输入、保存按钮样式。

- [ ] **Step 6: 预览测试**

从分包路径进入页面，搜索“血压”，选择后保存，确认数据库生成记录。

- [ ] **Step 7: Commit**

```bash
git add miniprogram/pkg-system/pages/indicator-manual miniprogram/app.json
git commit -m "feat(frontend): manual indicator entry page

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

#### Task 3.3: OCR 失败引导手动录入

**目标：** 在 `upload` 页面 OCR 失败或结果为空时，提供“手动录入”按钮跳转。

**Files:**
- Modify: `miniprogram/pages/upload/upload.wxml`
- Modify: `miniprogram/pages/upload/upload.js`

**Interfaces:**
- Produces: `goToManualEntry()` 方法

**Steps:**

- [ ] **Step 1: 在 WXML 错误/空结果区域增加按钮**

```xml
<button class="manual-entry-btn" bindtap="goToManualEntry">手动录入</button>
```

- [ ] **Step 2: 实现跳转方法**

```javascript
goToManualEntry() {
  wx.navigateTo({
    url: `/pkg-system/pages/indicator-manual/indicator-manual?member_id=${this.data.memberId}`,
  });
},
```

- [ ] **Step 3: 预览测试**

上传一张无法识别的图片，出现手动录入按钮，点击正常跳转。

- [ ] **Step 4: Commit**

```bash
git add miniprogram/pages/upload/upload.wxml miniprogram/pages/upload/upload.js
git commit -m "feat(frontend): navigate to manual entry when OCR fails

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Phase 3: 慢性病专区（依赖 Task 3.1 指标搜索）

#### Task 4.1: 后端慢性病套餐 API

**目标：** 定义高血压、糖尿病、高血脂三个套餐，返回相关指标、参考范围、AI/规则病情简报。

**Files:**
- Create: `backend/app/core/chronic_packages.py`
- Create: `backend/app/schemas/chronic.py`
- Modify: `backend/app/api/indicators.py`
- Create: `backend/tests/unit/test_chronic_packages.py`
- Create: `backend/tests/integration/test_chronic.py`

**Interfaces:**
- Consumes: `indicator_search.search_indicators`, `indicator_engine.evaluate_indicator`（或自行判断 status）
- Produces:
  - `GET /api/indicators/chronic` → `list[ChronicPackageListItem]`
  - `GET /api/indicators/chronic/{package}?member_id={id}` → `ChronicPackageResponse`
  - `package` 枚举：`hypertension` | `diabetes` | `dyslipidemia`

**Steps:**

- [ ] **Step 1: 编写 Schema**

```python
# backend/app/schemas/chronic.py
from pydantic import BaseModel

class ChronicIndicatorItem(BaseModel):
    key: str
    name: str
    value: float | None
    unit: str
    status: str
    ref_range: str | None

class ChronicPackageResponse(BaseModel):
    package: str
    name: str
    indicators: list[ChronicIndicatorItem]
    summary: str
```

- [ ] **Step 2: 编写套餐定义**

```python
# backend/app/core/chronic_packages.py
CHRONIC_PACKAGES = {
    "hypertension": {
        "name": "高血压",
        "indicators": ["systolic_bp", "diastolic_bp"],
    },
    "diabetes": {
        "name": "糖尿病",
        "indicators": ["fasting_glucose"],
    },
    "dyslipidemia": {
        "name": "高血脂",
        "indicators": ["total_cholesterol", "ldl"],
    },
}

def build_chronic_package(package: str, member_id: int, db: AsyncSession) -> ChronicPackageResponse:
    ...
```

- [ ] **Step 3: 实现 summary 生成**

- 无 AI key：基于指标状态拼接规则文本（如“血压偏高，建议就医”）。
- 有 AI key：调用 `ai_service` / `factory.chat_with_fallback` 生成简短病情简报。

- [ ] **Step 4: 注册 API**

```python
# backend/app/api/indicators.py
@router.get("/chronic")
async def list_chronic_packages(...):
    return [...]

@router.get("/chronic/{package}")
async def get_chronic_package(package: str, member_id: int, ...):
    ...
```

- [ ] **Step 5: 编写并运行测试**

```bash
python -m pytest tests/unit/test_chronic_packages.py tests/integration/test_chronic.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/chronic_packages.py backend/app/schemas/chronic.py backend/app/api/indicators.py backend/tests/unit/test_chronic_packages.py backend/tests/integration/test_chronic.py
git commit -m "feat(backend): chronic disease package endpoints

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

#### Task 4.2: 前端慢性病专区页面与入口

**目标：** 在“我的”页增加入口，新增慢性病专区列表与详情页。

**Files:**
- Create: `miniprogram/pkg-system/pages/chronic/chronic.{json,wxml,wxss,js}`
- Modify: `miniprogram/pages/profile/profile.wxml`
- Modify: `miniprogram/pages/profile/profile.js`
- Modify: `miniprogram/app.json`

**Interfaces:**
- Consumes: `GET /api/indicators/chronic`, `GET /api/indicators/chronic/{package}?member_id={id}`

**Steps：**

- [ ] **Step 1: 创建页面文件并注册到 `pkg-system` 分包**
- [ ] **Step 2: 列表页展示三个套餐卡片**
- [ ] **Step 3: 详情页展示指标列表与 AI 简报**
- [ ] **Step 4: 在 profile 页增加“慢性病专区”入口按钮**
- [ ] **Step 5: 预览测试**
- [ ] **Step 6: Commit**

```bash
git add miniprogram/pkg-system/pages/chronic miniprogram/pages/profile/profile.wxml miniprogram/pages/profile/profile.js miniprogram/app.json
git commit -m "feat(frontend): chronic disease zone pages and profile entry

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Phase 4: 儿童成长与发育（可与 Phase 2/3 并行）

#### Task 5.1: GrowthRecord 模型与迁移

**目标：** 新增 `growth_records` 表，记录儿童身高/体重/头围/BMI 与测量日期。

**Files:**
- Create: `backend/app/models/growth_record.py`
- Modify: `backend/app/models/member.py`
- Modify: `backend/app/models/__init__.py`（若需要显式导出）
- Create: `backend/alembic/versions/xxxx_add_growth_records_table.py`

**Schema (SQLAlchemy):**

```python
class GrowthRecord(Base):
    __tablename__ = "growth_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), index=True)
    record_type: Mapped[str]  # height / weight / head_circumference / bmi
    value: Mapped[float]
    unit: Mapped[str]
    recorded_at: Mapped[date]
    created_at: Mapped[datetime] = mapped_column(default=func.now())
```

**Steps:**

- [ ] **Step 1: 编写模型**
- [ ] **Step 2: 在 Member 中增加 relationship**
- [ ] **Step 3: 生成 Alembic 迁移**

```bash
cd backend
alembic revision --autogenerate -m "add growth_records table"
alembic upgrade head
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/growth_record.py backend/app/models/member.py backend/alembic/versions/xxxx_add_growth_records_table.py
git commit -m "feat(backend): add growth_records model and migration

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

#### Task 5.2: 后端儿童成长 API

**目标：** 实现成长记录 CRUD 与里程碑接口。

**Files:**
- Create: `backend/app/schemas/growth.py`
- Create: `backend/app/core/milestone_data.py`
- Create: `backend/app/api/child.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/unit/test_milestone_data.py`
- Create: `backend/tests/integration/test_child_growth.py`

**Interfaces:**
- Produces:
  - `POST /api/child/growth` → `GrowthRecordOut`
  - `GET /api/child/growth?member_id={id}&type={type}` → `list[GrowthRecordOut]`
  - `DELETE /api/child/growth/{record_id}` → 204
  - `GET /api/child/milestones?member_id={id}` → `list[MilestoneItem]`

**Steps：**

- [ ] **Step 1: 编写 Schema**
- [ ] **Step 2: 编写里程碑静态数据**
- [ ] **Step 3: 编写 child router 并注册到 main.py**
- [ ] **Step 4: 编写测试并运行**

```bash
python -m pytest tests/unit/test_milestone_data.py tests/integration/test_child_growth.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/growth.py backend/app/core/milestone_data.py backend/app/api/child.py backend/app/main.py backend/tests/unit/test_milestone_data.py backend/tests/integration/test_child_growth.py
git commit -m "feat(backend): child growth and milestone APIs

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

#### Task 5.3: 前端成长曲线与里程碑页面

**目标：** 在 `pkg-child` 分包新增 growth 和 milestone 页面，并在儿童 dashboard 添加入口。

**Files:**
- Create: `miniprogram/pkg-child/pages/growth/growth.{json,wxml,wxss,js}`
- Create: `miniprogram/pkg-child/pages/milestone/milestone.{json,wxml,wxss,js}`
- Modify: `miniprogram/pkg-child/pages/child-dashboard/child-dashboard.{js,wxml}`
- Modify: `miniprogram/app.json`

**Interfaces:**
- Consumes: `GET /api/child/growth`, `POST /api/child/growth`, `DELETE /api/child/growth/{id}`, `GET /api/child/milestones`

**Steps：**

- [ ] **Step 1: 创建 growth 页面**
  - 列表展示历史记录
  - 使用 `canvas` 绘制简单折线图（或先用 `ec-canvas` 如项目已引入，否则用简单 CSS/Canvas）
  - 添加记录弹窗/表单
- [ ] **Step 2: 创建 milestone 页面**
  - 按年龄分组展示里程碑
  - 标记已完成/待完成
- [ ] **Step 3: 在 child-dashboard 增加入口**
  - 将“生长”快捷入口从跳转 indicators 改为 `goToGrowth()`
  - 增加“发育里程碑”入口
- [ ] **Step 4: 在 app.json 注册分包页面**
- [ ] **Step 5: 预览测试**
- [ ] **Step 6: Commit**

```bash
git add miniprogram/pkg-child/pages/growth miniprogram/pkg-child/pages/milestone miniprogram/pkg-child/pages/child-dashboard miniprogram/app.json
git commit -m "feat(frontend): child growth and milestone pages

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Phase 5: 真实 OCR（依赖 Task 3.1 指标标准化，放最后）

#### Task 6.1: OCR Provider 抽象与配置

**目标：** 在 `backend/app/ai/` 下新增 OCR Provider 抽象与工厂，并在 `config.py` 增加配置项。

**Files:**
- Create: `backend/app/ai/ocr_provider.py`
- Modify: `backend/app/ai/factory.py`
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`

**Interfaces:**
- Produces:
  - `OCRProvider.extract_text(image_url: str) -> str`
  - `OCRProvider.extract_indicators(image_url: str) -> list[dict]`
  - `ProviderFactory.get_ocr_provider(name: str) -> OCRProvider`
  - `ocr_with_fallback(image_url: str) -> list[dict]`

**Config 新增项：**

```python
OCR_PROVIDER: str = "mock"  # mock | baidu | tencent
BAIDU_OCR_API_KEY: str = ""
BAIDU_OCR_SECRET_KEY: str = ""
TENCENT_OCR_SECRET_ID: str = ""
TENCENT_OCR_SECRET_KEY: str = ""
```

**Steps：**

- [ ] **Step 1: 编写 OCRProvider ABC**
- [ ] **Step 2: 扩展 factory.py**
- [ ] **Step 3: 修改 config.py**
- [ ] **Step 4: 更新 .env.example**
- [ ] **Step 5: Commit**

```bash
git add backend/app/ai/ocr_provider.py backend/app/ai/factory.py backend/app/config.py backend/.env.example
git commit -m "feat(backend): OCR provider abstraction and configuration

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

#### Task 6.2: Baidu OCR Provider 实现

**目标：** 实现百度云通用文字识别 + 指标提取。

**Files:**
- Create: `backend/app/ai/baidu_ocr_provider.py`
- Create: `backend/tests/unit/test_baidu_ocr_provider.py`

**Steps：**

- [ ] **Step 1: 实现 access_token 获取**
- [ ] **Step 2: 实现图片 OCR 调用**
- [ ] **Step 3: 实现 extract_indicators（文本 → 指标列表）**
  - 使用 `indicator_search` / `indicator_normalizer` 匹配指标名
  - 正则提取数值与单位
- [ ] **Step 4: 编写单元测试（mock 百度 API）**
- [ ] **Step 5: Commit**

```bash
git add backend/app/ai/baidu_ocr_provider.py backend/tests/unit/test_baidu_ocr_provider.py
git commit -m "feat(backend): Baidu OCR provider implementation

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

#### Task 6.3: OCR Pipeline 与 Reports API 接入

**目标：** 创建 `ocr_pipeline.py`，在 `POST /api/reports/{id}/ocr` 中调用真实 Provider。

**Files:**
- Create: `backend/app/services/ocr_pipeline.py`
- Create: `backend/app/schemas/ocr.py`
- Modify: `backend/app/core/ocr_service.py`（保留 mock/regex fallback）
- Modify: `backend/app/api/reports.py`
- Create: `backend/tests/unit/test_ocr_pipeline.py`
- Create: `backend/tests/integration/test_ocr_real.py`

**Interfaces:**
- Produces:
  - `OCRPipeline.run(report_id: int, member_id: int) -> OCRResult`
  - `POST /api/reports/{id}/ocr` 保持现有接口不变

**Steps：**

- [ ] **Step 1: 编写 OCRResult Schema**
- [ ] **Step 2: 编写 OCRPipeline**
  - 读取 report 图片路径
  - 调用 `ocr_with_fallback()`
  - 用 `indicator_search` 标准化指标名
  - 创建 `IndicatorData` 记录
- [ ] **Step 3: 修改 reports.py 接入 pipeline**
- [ ] **Step 4: 编写测试**
- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ocr_pipeline.py backend/app/schemas/ocr.py backend/app/core/ocr_service.py backend/app/api/reports.py backend/tests/unit/test_ocr_pipeline.py backend/tests/integration/test_ocr_real.py
git commit -m "feat(backend): real OCR pipeline integration

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## 最终验证清单

- [ ] Task 2：指标矩阵后端测试全部通过；前端矩阵视图可切换、可滚动、可点击。
- [ ] Task 3：手动录入页可搜索、选择、保存；OCR 失败页可跳转。
- [ ] Task 4：慢性病列表与详情页正常；profile 入口可进入。
- [ ] Task 5：成长记录可增删查；里程碑可展示；迁移已应用到开发库。
- [ ] Task 6：OCR Pipeline 在配置真实 key 后可提取指标；无 key 时回退 mock。
- [ ] 全部后端测试通过：`pytest -q`
- [ ] ruff + mypy 无新增错误。
- [ ] 未误提交 `.mysql_data/`、`uploads/`、`e2e/screenshots/`。

---

## 已知注意事项

- **运行测试时必须使用 `python -m pytest`，直接执行 `pytest` 会因路径问题导致 `ModuleNotFoundError: No module named 'app'`。**
- Task 2 已提交一次进度 commit，后续完成时应追加最终 commit，不要修改历史。
- Task 5 涉及数据库迁移，执行前需确认本地 MySQL（端口 3308）已启动。
- Task 6 中 Tencent OCR 当前为占位实现，真实接入需引入 `tencentcloud-sdk-python`。
- 前端 `api.js` 的返回值 unwrap 方式可能与其他页面不同，实现前请确认当前 `api.get/post` 返回的是 response 对象还是 `response.data`。
- 儿童 dashboard 当前“生长”快捷入口跳转的是通用 indicators 页，完成 Task 5 后需改跳 `growth` 页。
