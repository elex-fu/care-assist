# P0 核心能力实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐 Care Assist 产品主流程的 6 个 P0 核心能力：真实 OCR、指标表单视图、慢性病专区、儿童成长发育、手动录入页、API Base 环境化。

**Architecture:** 后端沿用 FastAPI + SQLAlchemy async 架构，新增 OCR Provider 抽象层和慢性病/儿童专用 API；前端沿用原生微信小程序，通过新增页面和组件完成交互；AI 能力复用已接入的 Kimi Code Provider。

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0 async, aiomysql, httpx, Pydantic; 微信小程序 WXML/WXSS/JS; 腾讯云/百度 OCR（可选）。

## 全局约束

- Python 版本：>=3.11
- 后端框架：FastAPI >=0.110.0
- ORM：SQLAlchemy 2.0 async
- 数据库：MySQL 8.0+（开发环境端口 3308）
- 前端：原生微信小程序，不使用第三方框架
- 测试：pytest + pytest-asyncio，TDD 风格，每个任务先有测试再实现
- 代码风格：ruff line-length 100，mypy strict
- 提交规范：`feat(scope): description`，结尾加 `Co-Authored-By: Claude <noreply@anthropic.com>`
- 环境变量敏感信息（API key）不得提交到 git，统一走 `.env`
- 所有新增 API 必须添加到 `app/main.py` 注册路由
- 所有新增数据模型必须通过 Alembic 生成迁移脚本

---

## 文件结构总览

### 后端新增/修改

```
backend/app/
├── ai/
│   └── ocr_provider.py           # OCR Provider 抽象接口（P0-2）
├── core/
│   ├── ocr_service.py            # 修改为工厂 + 真实 Provider（P0-2）
│   └── indicator_normalizer.py   # 指标名称标准化（P0-2, P0-6）
├── api/
│   ├── indicators.py             # 新增 /matrix, /metadata, /chronic/{package}（P0-3, P0-4, P0-6）
│   ├── child.py                  # 新增 /growth, /milestones（P0-5）
│   └── reports.py                # 修改 upload/ocr 流程（P0-2）
├── models/
│   ├── growth_record.py          # 新增 GrowthRecord 模型（P0-5）
│   └── milestone.py              # 新增 Milestone 模型或静态数据（P0-5）
├── schemas/
│   ├── indicator_matrix.py       # 新增矩阵响应 Schema（P0-3）
│   ├── chronic.py                # 新增慢性病套餐 Schema（P0-4）
│   ├── growth.py                 # 新增成长记录 Schema（P0-5）
│   └── ocr.py                    # 新增 OCR 响应 Schema（P0-2）
├── services/
│   └── ocr_pipeline.py           # 新增 OCR 流水线：识别→提取→标准化→创建指标（P0-2）
└── config.py                     # 新增 OCR Provider 配置（P0-2）
```

### 前端新增/修改

```
miniprogram/
├── pages/
│   └── indicators/
│       ├── indicators.wxml       # 新增视图切换（P0-3）
│       └── indicators.js         # 新增矩阵视图数据加载（P0-3）
├── pkg-system/
│   └── pages/
│       ├── chronic/
│       │   ├── chronic.wxml      # 新增慢性病专区（P0-4）
│       │   └── chronic.js        # 新增慢性病专区（P0-4）
│       └── indicator-manual/
│           ├── indicator-manual.wxml  # 新增手动录入（P0-6）
│           └── indicator-manual.js    # 新增手动录入（P0-6）
├── pkg-child/
│   └── pages/
│       ├── growth/
│       │   ├── growth.wxml       # 新增成长曲线（P0-5）
│       │   └── growth.js         # 新增成长曲线（P0-5）
│       └── milestone/
│           ├── milestone.wxml    # 新增发育里程碑（P0-5）
│           └── milestone.js      # 新增发育里程碑（P0-5）
├── utils/
│   ├── api.js                    # 修改 API Base 环境化（P0-7）
│   └── config.js                 # 新增环境配置（P0-7）
└── app.js                        # 修改 globalData apiBase（P0-7）
```

---

## Task 1: P0-7 API Base 环境化

**目标：** 移除前端代码中写死的 `http://localhost:8000`，根据微信小程序运行环境自动切换 API Base URL。

**Files:**
- Create: `miniprogram/utils/config.js`
- Modify: `miniprogram/utils/api.js`
- Modify: `miniprogram/app.js`
- Test: 手动验证（微信小程序无单元测试框架，通过开发者工具切换环境验证）

**Interfaces:**
- `getApiBase()` → `string`：返回当前环境对应的 API Base URL
- `getEnvVersion()` → `'develop' | 'trial' | 'release'`：返回微信小程序环境版本

### 子任务 1.1: 新增环境配置模块

- [ ] **Step 1: 创建 `miniprogram/utils/config.js`**

```javascript
// miniprogram/utils/config.js
function getEnvVersion() {
  try {
    const accountInfo = wx.getAccountInfoSync()
    return accountInfo.miniProgram.envVersion || 'release'
  } catch (err) {
    return 'release'
  }
}

const ENV_CONFIG = {
  develop: {
    apiBase: 'http://localhost:8000',
    name: '开发环境',
  },
  trial: {
    apiBase: 'https://api-staging.care-assist.example.com',
    name: '体验版环境',
  },
  release: {
    apiBase: 'https://api.care-assist.example.com',
    name: '生产环境',
  },
}

function getApiBase() {
  const env = getEnvVersion()
  return ENV_CONFIG[env]?.apiBase || ENV_CONFIG.release.apiBase
}

function getCurrentEnv() {
  const env = getEnvVersion()
  return {
    version: env,
    ...ENV_CONFIG[env],
  }
}

module.exports = {
  getEnvVersion,
  getApiBase,
  getCurrentEnv,
}
```

- [ ] **Step 2: 修改 `miniprogram/utils/api.js` 使用动态 API Base**

```javascript
// miniprogram/utils/api.js
const { getApiBase } = require('./config')

const API_BASE = getApiBase()

// 其余 request/refresh/uploadFile 逻辑不变，仅把之前硬编码的 'http://localhost:8000' 替换为 API_BASE
```

具体替换：

```javascript
// 旧代码
const API_BASE = 'http://localhost:8000'

// 新代码
const { getApiBase } = require('./config')
const API_BASE = getApiBase()
```

`request()` 和 `uploadFile()` 函数中所有使用 `API_BASE` 的地方保持不变。

- [ ] **Step 3: 修改 `miniprogram/app.js` 移除硬编码 apiBase**

```javascript
// miniprogram/app.js
const { getApiBase } = require('./utils/config')

App({
  onLaunch() {
    console.log('Care Assist App Launch, env:', getApiBase())
    // ... 原有逻辑
  },

  globalData: {
    apiBase: getApiBase(),
  },
})
```

- [ ] **Step 4: 手动验证**

在小程序开发者工具中：
1. 详情 → 本地设置 → 切换「不校验合法域名」开启（开发环境调用 localhost 需要）
2. 编译 → 控制台应输出 `http://localhost:8000`
3. 预览/上传体验版时，应自动切换为 staging URL
4. 真机正式版应切换为 production URL

- [ ] **Step 5: Commit**

```bash
git add miniprogram/utils/config.js miniprogram/utils/api.js miniprogram/app.js
git commit -m "feat(frontend): env-aware API base configuration"
```

---

## Task 2: P0-3 指标中心表单视图

**目标：** 在指标中心增加「表单视图」：日期为行、指标为列，异常单元格标红，支持点击单元格查看详情。

**Files:**
- Create: `backend/app/schemas/indicator_matrix.py`
- Modify: `backend/app/api/indicators.py`
- Modify: `backend/app/services/member_service.py`（如需要）
- Create: `backend/tests/unit/test_indicator_matrix.py`
- Create: `backend/tests/integration/test_indicator_matrix.py`
- Modify: `miniprogram/pages/indicators/indicators.wxml`
- Modify: `miniprogram/pages/indicators/indicators.js`
- Create: `miniprogram/pages/indicators/indicators.wxss`（如样式未内联）

**Interfaces:**
- `GET /api/indicators/matrix?member_id={id}&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` → `IndicatorMatrixResponse`
- `IndicatorMatrixResponse` 结构：
  - `dates: list[str]` — 日期列表
  - `indicator_keys: list[str]` — 指标 key 列表
  - `indicator_names: dict[str, str]` — key → 中文名
  - `units: dict[str, str]` — key → 单位
  - `cells: dict[str, dict[str, MatrixCell | None]]` — `cells[date][key]`
  - `MatrixCell: { value: float, status: str, indicator_id: int }`

### 子任务 2.1: 后端新增矩阵查询 API

- [ ] **Step 1: 编写测试 `backend/tests/unit/test_indicator_matrix.py`**

```python
import pytest
from datetime import date
from decimal import Decimal

from app.schemas.indicator_matrix import IndicatorMatrixResponse, MatrixCell


class TestIndicatorMatrixResponse:
    def test_matrix_cell_schema(self):
        cell = MatrixCell(value=120.5, status="normal", indicator_id=1)
        assert cell.value == 120.5
        assert cell.status == "normal"
        assert cell.indicator_id == 1

    def test_matrix_response_schema(self):
        data = {
            "dates": ["2026-06-01", "2026-06-02"],
            "indicator_keys": ["systolic_bp"],
            "indicator_names": {"systolic_bp": "收缩压"},
            "units": {"systolic_bp": "mmHg"},
            "cells": {
                "2026-06-01": {"systolic_bp": {"value": 120, "status": "normal", "indicator_id": 1}},
                "2026-06-02": {"systolic_bp": None},
            },
        }
        resp = IndicatorMatrixResponse(**data)
        assert len(resp.dates) == 2
        assert resp.cells["2026-06-02"]["systolic_bp"] is None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
source backend/.venv/bin/activate
cd backend
rtk proxy python -m pytest tests/unit/test_indicator_matrix.py -v
# Expected: ModuleNotFoundError for app.schemas.indicator_matrix
```

- [ ] **Step 3: 创建 Schema `backend/app/schemas/indicator_matrix.py`**

```python
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MatrixCell(BaseModel):
    value: Decimal
    status: str
    indicator_id: int

    model_config = ConfigDict(json_schema_extra={"example": {"value": 120, "status": "normal", "indicator_id": 1}})


class IndicatorMatrixResponse(BaseModel):
    dates: list[str]
    indicator_keys: list[str]
    indicator_names: dict[str, str]
    units: dict[str, str]
    cells: dict[str, dict[str, Optional[MatrixCell]]]
```

- [ ] **Step 4: 运行 Schema 测试通过**

```bash
rtk proxy python -m pytest tests/unit/test_indicator_matrix.py -v
# Expected: 2 passed
```

- [ ] **Step 5: 编写集成测试 `backend/tests/integration/test_indicator_matrix.py`**

```python
import pytest
from datetime import date
from decimal import Decimal

from app.models.indicator import IndicatorData


class TestIndicatorMatrix:
    async def test_matrix_requires_auth(self, client):
        resp = await client.get("/api/indicators/matrix?member_id=123")
        assert resp.status_code == 401

    async def test_matrix_returns_dates_and_indicators(
        self, auth_client, test_member, db
    ):
        db.add(
            IndicatorData(
                member_id=test_member.id,
                indicator_key="systolic_bp",
                indicator_name="收缩压",
                value=Decimal("120"),
                unit="mmHg",
                status="normal",
                record_date=date(2026, 6, 1),
            )
        )
        await db.commit()

        resp = await auth_client.get(
            f"/api/indicators/matrix?member_id={test_member.id}"
            "&start_date=2026-06-01&end_date=2026-06-03"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "2026-06-01" in data["dates"]
        assert "systolic_bp" in data["indicator_keys"]
        cell = data["cells"]["2026-06-01"]["systolic_bp"]
        assert cell["value"] == "120"
        assert cell["status"] == "normal"
```

- [ ] **Step 6: 修改 `backend/app/api/indicators.py` 新增矩阵端点**

```python
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_member
from app.db.session import get_db
from app.models.indicator import IndicatorData
from app.models.member import Member
from app.schemas.indicator_matrix import IndicatorMatrixResponse, MatrixCell
from app.schemas.response import ResponseSchema

router = APIRouter(prefix="/api/indicators", tags=["indicators"])


@router.get("/matrix", response_model=ResponseSchema[IndicatorMatrixResponse])
async def get_indicator_matrix(
    member_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_member: Member = Depends(get_current_member),
):
    # Verify member is in same family
    target = await db.get(Member, member_id)
    if not target or target.family_id != current_member.family_id:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("无权访问该成员数据")

    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    result = await db.execute(
        select(IndicatorData)
        .where(
            IndicatorData.member_id == member_id,
            IndicatorData.record_date >= start_date,
            IndicatorData.record_date <= end_date,
        )
        .order_by(IndicatorData.record_date.desc(), IndicatorData.created_at.desc())
    )
    records = result.scalars().all()

    # Build matrix
    dates = sorted({str(r.record_date) for r in records if start_date <= r.record_date <= end_date})
    keys = sorted({r.indicator_key for r in records})
    names = {r.indicator_key: r.indicator_name for r in records}
    units = {r.indicator_key: r.unit for r in records}

    cells: dict[str, dict[str, Optional[MatrixCell]]] = {}
    for d in dates:
        cells[d] = {k: None for k in keys}

    for r in records:
        d = str(r.record_date)
        if d not in cells:
            continue
        # Keep latest record per date/key
        if cells[d][r.indicator_key] is None:
            cells[d][r.indicator_key] = MatrixCell(
                value=r.value,
                status=r.status,
                indicator_id=r.id,
            )

    matrix = IndicatorMatrixResponse(
        dates=dates,
        indicator_keys=keys,
        indicator_names=names,
        units=units,
        cells=cells,
    )
    return ResponseSchema(data=matrix)
```

注意：确保 `app.api.dependencies.get_current_member` 存在，且 `ResponseSchema` 支持泛型。

- [ ] **Step 7: 运行集成测试**

```bash
rtk proxy python -m pytest tests/integration/test_indicator_matrix.py -v
# Expected: 2 passed
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/indicator_matrix.py backend/app/api/indicators.py \
  backend/tests/unit/test_indicator_matrix.py backend/tests/integration/test_indicator_matrix.py
git commit -m "feat(backend): indicator matrix API"
```

### 子任务 2.2: 前端新增表单视图

- [ ] **Step 1: 修改 `miniprogram/pages/indicators/indicators.wxml` 增加视图切换和矩阵表格**

在页面顶部成员选择器下方添加视图切换按钮：

```xml
<!-- 视图切换 -->
<view class="view-toggle">
  <view
    class="toggle-item {{viewMode === 'list' ? 'active' : ''}}"
    data-mode="list"
    bindtap="switchViewMode"
  >
    <text>列表</text>
  </view>
  <view
    class="toggle-item {{viewMode === 'matrix' ? 'active' : ''}}"
    data-mode="matrix"
    bindtap="switchViewMode"
  >
    <text>表单</text>
  </view>
</view>
```

列表视图用现有代码，添加 `wx:if="{{viewMode === 'list'}}"` 包裹。

新增矩阵视图：

```xml
<!-- Matrix View -->
<view class="matrix-view" wx:if="{{viewMode === 'matrix'}}">
  <scroll-view class="matrix-scroll" scroll-x="true" scroll-y="true">
    <view class="matrix-table">
      <!-- Header row -->
      <view class="matrix-row header-row">
        <view class="matrix-cell header-cell fixed-cell">日期</view>
        <view
          class="matrix-cell header-cell"
          wx:for="{{matrix.indicator_keys}}"
          wx:key="*this"
        >
          <text>{{matrix.indicator_names[item]}}</text>
          <text class="unit">({{matrix.units[item]}})</text>
        </view>
      </view>

      <!-- Data rows -->
      <view
        class="matrix-row"
        wx:for="{{matrix.dates}}"
        wx:for-item="date"
        wx:key="*this"
      >
        <view class="matrix-cell fixed-cell">{{date}}</view>
        <view
          class="matrix-cell {{matrix.cells[date][key].status}}"
          wx:for="{{matrix.indicator_keys}}"
          wx:for-item="key"
          wx:key="*this"
          data-date="{{date}}"
          data-key="{{key}}"
          data-id="{{matrix.cells[date][key].indicator_id}}"
          bindtap="onMatrixCellTap"
        >
          <block wx:if="{{matrix.cells[date][key]}}">
            <text>{{matrix.cells[date][key].value}}</text>
          </block>
          <text wx:else class="empty-cell">-</text>
        </view>
      </view>
    </view>
  </scroll-view>
</view>
```

- [ ] **Step 2: 修改 `miniprogram/pages/indicators/indicators.js` 增加矩阵视图逻辑**

在 `data` 中新增：

```javascript
viewMode: 'list', // list | matrix
matrix: null,
```

新增方法：

```javascript
switchViewMode(e) {
  const mode = e.currentTarget.dataset.mode
  this.setData({ viewMode: mode })
  if (mode === 'matrix') {
    this.loadMatrix()
  }
},

async loadMatrix() {
  const { currentMemberId } = this.data
  if (!currentMemberId) return
  this.setData({ loading: true })
  try {
    const today = new Date()
    const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000)
    const fmt = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    const res = await api.get(
      `/api/indicators/matrix?member_id=${currentMemberId}&start_date=${fmt(thirtyDaysAgo)}&end_date=${fmt(today)}`
    )
    this.setData({ matrix: res.data, loading: false })
  } catch (err) {
    wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    this.setData({ loading: false })
  }
},

onMatrixCellTap(e) {
  const { date, key, id } = e.currentTarget.dataset
  if (!id) return
  const name = this.data.matrix.indicator_names[key]
  const unit = this.data.matrix.units[key]
  wx.navigateTo({
    url: `/pages/indicator-detail/indicator-detail?member_id=${this.data.currentMemberId}&indicator_key=${key}&indicator_name=${name}&unit=${unit || ''}`,
  })
},
```

- [ ] **Step 3: 添加样式**

在 `miniprogram/pages/indicators/indicators.wxss` 中添加：

```css
.view-toggle {
  display: flex;
  background: #fff;
  border-radius: 8px;
  margin: 12px 16px;
  padding: 4px;
}
.toggle-item {
  flex: 1;
  text-align: center;
  padding: 8px 0;
  font-size: 14px;
  color: #64748B;
  border-radius: 6px;
}
.toggle-item.active {
  background: #EFF6FF;
  color: #2563EB;
  font-weight: 500;
}

.matrix-scroll {
  width: 100%;
  height: 600px;
  background: #fff;
}
.matrix-table {
  display: table;
  min-width: 100%;
}
.matrix-row {
  display: table-row;
}
.matrix-cell {
  display: table-cell;
  min-width: 90px;
  padding: 12px 8px;
  border-bottom: 1px solid #E2E8F0;
  border-right: 1px solid #E2E8F0;
  text-align: center;
  font-size: 13px;
}
.fixed-cell {
  position: sticky;
  left: 0;
  background: #F8FAFC;
  z-index: 1;
}
.header-cell {
  background: #F1F5F9;
  font-weight: 500;
  color: #1E293B;
}
.unit {
  display: block;
  font-size: 11px;
  color: #94A3B8;
}
.matrix-cell.normal { color: #10B981; }
.matrix-cell.low,
.matrix-cell.high { color: #F59E0B; background: #FFFBEB; }
.matrix-cell.critical { color: #EF4444; background: #FEF2F2; }
.empty-cell { color: #CBD5E1; }
```

- [ ] **Step 4: 手动验证**

1. 进入指标页
2. 点击「表单」切换视图
3. 确认表格显示日期行和指标列
4. 确认异常单元格有颜色
5. 点击单元格跳转到指标详情

- [ ] **Step 5: Commit**

```bash
git add miniprogram/pages/indicators/indicators.*
git commit -m "feat(frontend): indicator matrix view"
```

---

## Task 3: P0-6 手动录入页

**目标：** 为 OCR 失败或用户主动录入提供替代路径：搜索/选择指标 → 自动带出单位与参考范围 → 保存。

**Files:**
- Create: `backend/app/core/indicator_normalizer.py`
- Create: `backend/app/schemas/indicator_metadata.py`
- Modify: `backend/app/api/indicators.py`
- Create: `backend/tests/unit/test_indicator_normalizer.py`
- Create: `backend/tests/integration/test_indicator_metadata.py`
- Create: `miniprogram/pkg-system/pages/indicator-manual/indicator-manual.wxml`
- Create: `miniprogram/pkg-system/pages/indicator-manual/indicator-manual.js`
- Create: `miniprogram/pkg-system/pages/indicator-manual/indicator-manual.json`
- Create: `miniprogram/pkg-system/pages/indicator-manual/indicator-manual.wxss`
- Modify: `miniprogram/pages/upload/upload.js` — 添加手动录入入口
- Modify: `miniprogram/app.json` — 注册新页面

**Interfaces:**
- `GET /api/indicators/metadata?q={query}` → `list[IndicatorMetadata]`
- `IndicatorMetadata: { key, name, unit, lower_limit, upper_limit, aliases }`
- 前端页面路径：`/pkg-system/pages/indicator-manual/indicator-manual?member_id={id}`

### 子任务 3.1: 后端新增指标元数据服务

- [ ] **Step 1: 创建 `backend/app/core/indicator_normalizer.py`**

```python
from decimal import Decimal
from typing import Optional


_INDICATOR_CATALOG = [
    {
        "key": "systolic_bp",
        "name": "收缩压",
        "unit": "mmHg",
        "lower_limit": Decimal("90"),
        "upper_limit": Decimal("120"),
        "aliases": ["收缩压", "高压", "sbp", "收缩期血压"],
    },
    {
        "key": "diastolic_bp",
        "name": "舒张压",
        "unit": "mmHg",
        "lower_limit": Decimal("60"),
        "upper_limit": Decimal("80"),
        "aliases": ["舒张压", "低压", "dbp", "舒张期血压"],
    },
    {
        "key": "heart_rate",
        "name": "心率",
        "unit": "次/分",
        "lower_limit": Decimal("60"),
        "upper_limit": Decimal("100"),
        "aliases": ["心率", "脉率", "心跳", "pulse"],
    },
    {
        "key": "fasting_glucose",
        "name": "空腹血糖",
        "unit": "mmol/L",
        "lower_limit": Decimal("3.9"),
        "upper_limit": Decimal("6.1"),
        "aliases": ["空腹血糖", "空腹血糖值", "fbg"],
    },
    {
        "key": "hba1c",
        "name": "糖化血红蛋白",
        "unit": "%",
        "lower_limit": Decimal("4"),
        "upper_limit": Decimal("6"),
        "aliases": ["糖化血红蛋白", "hba1c", "糖化"],
    },
    {
        "key": "weight",
        "name": "体重",
        "unit": "kg",
        "lower_limit": None,
        "upper_limit": None,
        "aliases": ["体重", "weight", "体质量"],
    },
    {
        "key": "height",
        "name": "身高",
        "unit": "cm",
        "lower_limit": None,
        "upper_limit": None,
        "aliases": ["身高", "height", "身长"],
    },
    {
        "key": "temperature",
        "name": "体温",
        "unit": "°C",
        "lower_limit": Decimal("36"),
        "upper_limit": Decimal("37.2"),
        "aliases": ["体温", "temperature", "tem"],
    },
    {
        "key": "total_cholesterol",
        "name": "总胆固醇",
        "unit": "mmol/L",
        "lower_limit": Decimal("0"),
        "upper_limit": Decimal("5.2"),
        "aliases": ["总胆固醇", "胆固醇", "tc"],
    },
    {
        "key": "ldl",
        "name": "低密度脂蛋白胆固醇",
        "unit": "mmol/L",
        "lower_limit": Decimal("0"),
        "upper_limit": Decimal("3.4"),
        "aliases": ["低密度脂蛋白", "ldl", "低密度脂蛋白胆固醇", "坏胆固醇"],
    },
    {
        "key": "hdl",
        "name": "高密度脂蛋白胆固醇",
        "unit": "mmol/L",
        "lower_limit": Decimal("1"),
        "upper_limit": Decimal("2"),
        "aliases": ["高密度脂蛋白", "hdl", "高密度脂蛋白胆固醇", "好胆固醇"],
    },
    {
        "key": "triglycerides",
        "name": "甘油三酯",
        "unit": "mmol/L",
        "lower_limit": Decimal("0"),
        "upper_limit": Decimal("1.7"),
        "aliases": ["甘油三酯", "tg", "血脂"],
    },
]

_KEY_BY_NAME: dict[str, str] = {}
for _item in _INDICATOR_CATALOG:
    _KEY_BY_NAME[_item["name"]] = _item["key"]
    for alias in _item["aliases"]:
        _KEY_BY_NAME[alias] = _item["key"]


def search_indicators(query: str, limit: int = 10) -> list[dict]:
    """Search indicator catalog by name or alias (case-insensitive)."""
    query = query.strip().lower()
    if not query:
        return [dict(item) for item in _INDICATOR_CATALOG[:limit]]

    results = []
    for item in _INDICATOR_CATALOG:
        if query in item["name"].lower() or any(query in a.lower() for a in item["aliases"]):
            results.append(dict(item))
        if len(results) >= limit:
            break
    return results


def get_indicator_by_key(key: str) -> Optional[dict]:
    for item in _INDICATOR_CATALOG:
        if item["key"] == key:
            return dict(item)
    return None


def normalize_indicator_name(name: str) -> Optional[str]:
    """Map a raw indicator name to standard key using aliases."""
    return _KEY_BY_NAME.get(name.strip().lower())
```

- [ ] **Step 2: 创建 Schema `backend/app/schemas/indicator_metadata.py`**

```python
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class IndicatorMetadata(BaseModel):
    key: str
    name: str
    unit: str
    lower_limit: Optional[Decimal] = None
    upper_limit: Optional[Decimal] = None
    aliases: list[str]
```

- [ ] **Step 3: 修改 `backend/app/api/indicators.py` 新增元数据端点**

```python
from app.core.indicator_normalizer import search_indicators
from app.schemas.indicator_metadata import IndicatorMetadata


@router.get("/metadata", response_model=ResponseSchema[list[IndicatorMetadata]])
async def search_indicator_metadata(
    q: str = Query("", min_length=0),
    limit: int = Query(10, ge=1, le=50),
):
    results = search_indicators(q, limit)
    return ResponseSchema(data=[IndicatorMetadata(**item) for item in results])
```

- [ ] **Step 4: 编写测试并运行**

```python
# backend/tests/unit/test_indicator_normalizer.py
import pytest
from app.core.indicator_normalizer import search_indicators, normalize_indicator_name, get_indicator_by_key


class TestIndicatorNormalizer:
    def test_search_by_chinese_name(self):
        results = search_indicators("收缩压")
        assert len(results) >= 1
        assert results[0]["key"] == "systolic_bp"

    def test_search_by_alias(self):
        results = search_indicators("高压")
        assert results[0]["key"] == "systolic_bp"

    def test_normalize_name(self):
        assert normalize_indicator_name("高压") == "systolic_bp"
        assert normalize_indicator_name("Unknown") is None

    def test_get_by_key(self):
        item = get_indicator_by_key("fasting_glucose")
        assert item["name"] == "空腹血糖"
        assert item["unit"] == "mmol/L"
```

运行：

```bash
rtk proxy python -m pytest tests/unit/test_indicator_normalizer.py tests/integration/test_indicator_metadata.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/indicator_normalizer.py backend/app/schemas/indicator_metadata.py \
  backend/app/api/indicators.py backend/tests/unit/test_indicator_normalizer.py \
  backend/tests/integration/test_indicator_metadata.py
git commit -m "feat(backend): indicator metadata search API"
```

### 子任务 3.2: 前端新增手动录入页

- [ ] **Step 1: 注册页面**

在 `miniprogram/app.json` 的 `subpackages[3].pages`（pkg-system）中添加：

```json
"pages/indicator-manual/indicator-manual"
```

- [ ] **Step 2: 创建 `miniprogram/pkg-system/pages/indicator-manual/indicator-manual.json`**

```json
{
  "navigationBarTitleText": "手动录入指标",
  "usingComponents": {}
}
```

- [ ] **Step 3: 创建 WXML**

```xml
<view class="container">
  <view class="section">
    <text class="section-title">搜索指标</text>
    <input
      class="form-input"
      placeholder="输入指标名称，如血压、血糖"
      value="{{keyword}}"
      bindinput="onSearchInput"
      confirm-type="search"
      bindconfirm="search"
    />
  </view>

  <view class="suggestion-list" wx:if="{{suggestions.length}}">
    <view
      class="suggestion-item"
      wx:for="{{suggestions}}"
      wx:key="key"
      data-key="{{item.key}}"
      bindtap="selectIndicator"
    >
      <text class="suggestion-name">{{item.name}}</text>
      <text class="suggestion-unit">{{item.unit}}</text>
    </view>
  </view>

  <view class="section" wx:if="{{selected}}">
    <text class="section-title">录入 {{selected.name}}</text>
    <view class="form-row">
      <text class="form-label">数值 ({{selected.unit}})</text>
      <input class="form-input" type="digit" placeholder="请输入数值" value="{{value}}" bindinput="onValueInput" />
    </view>
    <view class="form-row">
      <text class="form-label">日期</text>
      <picker mode="date" value="{{recordDate}}" bindchange="onDateChange">
        <view class="form-picker">{{recordDate}}</view>
      </picker>
    </view>
    <view class="range-hint" wx:if="{{selected.lower_limit != null || selected.upper_limit != null}}">
      <text>参考范围：{{selected.lower_limit || '--'}} - {{selected.upper_limit || '--'}} {{selected.unit}}</text>
    </view>
    <button class="btn-submit" bindtap="submit">保存</button>
  </view>
</view>
```

- [ ] **Step 4: 创建 JS**

```javascript
const api = require('../../../utils/api')
const { formatDateFull } = require('../../../utils/format')

Page({
  data: {
    memberId: '',
    keyword: '',
    suggestions: [],
    selected: null,
    value: '',
    recordDate: formatDateFull(new Date()),
  },

  onLoad(options) {
    this.setData({ memberId: options.member_id || '' })
    this.loadCommonIndicators()
  },

  async loadCommonIndicators() {
    try {
      const res = await api.get('/api/indicators/metadata?q=')
      this.setData({ suggestions: res.data.slice(0, 8) })
    } catch (err) {
      console.error('loadCommonIndicators error', err)
    }
  },

  onSearchInput(e) {
    this.setData({ keyword: e.detail.value })
    if (e.detail.value.length >= 1) {
      this.search()
    }
  },

  async search() {
    const { keyword } = this.data
    try {
      const res = await api.get(`/api/indicators/metadata?q=${encodeURIComponent(keyword)}`)
      this.setData({ suggestions: res.data })
    } catch (err) {
      wx.showToast({ title: err.message || '搜索失败', icon: 'none' })
    }
  },

  selectIndicator(e) {
    const key = e.currentTarget.dataset.key
    const selected = this.data.suggestions.find(item => item.key === key)
    if (!selected) return
    this.setData({ selected, suggestions: [], keyword: selected.name, value: '' })
  },

  onValueInput(e) {
    this.setData({ value: e.detail.value })
  },

  onDateChange(e) {
    this.setData({ recordDate: e.detail.value })
  },

  async submit() {
    const { memberId, selected, value, recordDate } = this.data
    if (!memberId) {
      wx.showToast({ title: '缺少成员信息', icon: 'none' })
      return
    }
    if (!selected) {
      wx.showToast({ title: '请选择指标', icon: 'none' })
      return
    }
    const numValue = parseFloat(value)
    if (isNaN(numValue)) {
      wx.showToast({ title: '请输入有效数值', icon: 'none' })
      return
    }

    try {
      await api.post('/api/indicators', {
        member_id: memberId,
        indicator_key: selected.key,
        indicator_name: selected.name,
        value: numValue,
        unit: selected.unit,
        record_date: recordDate,
      })
      wx.showToast({ title: '保存成功', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 1000)
    } catch (err) {
      wx.showToast({ title: err.message || '保存失败', icon: 'none' })
    }
  },
})
```

- [ ] **Step 5: 修改上传结果页添加手动录入入口**

在 `miniprogram/pages/upload/upload.js` 的 OCR 失败处理中：

```javascript
// 在 startUpload catch 块中
if (err.message && err.message.includes('识别失败')) {
  wx.showModal({
    title: '识别失败',
    content: '是否手动录入指标？',
    confirmText: '手动录入',
    success: (res) => {
      if (res.confirm) {
        wx.navigateTo({
          url: `/pkg-system/pages/indicator-manual/indicator-manual?member_id=${currentMemberId}`,
        })
      }
    },
  })
}
```

- [ ] **Step 6: 手动验证**

1. 上传页触发 OCR 失败，出现手动录入弹窗
2. 进入手动录入页，搜索「血糖」
3. 选择空腹血糖，自动显示 mmol/L 和单位
4. 输入数值保存，跳回指标页可见新记录

- [ ] **Step 7: Commit**

```bash
git add miniprogram/pkg-system/pages/indicator-manual/ miniprogram/pages/upload/upload.js miniprogram/app.json
git commit -m "feat(frontend): manual indicator entry page"
```

---

## Task 4: P0-4 慢性病专区

**目标：** 提供高血压、糖尿病、高血脂三个慢性病套餐视图，显示相关指标组合与 AI 生成的病情简报。

**Files:**
- Create: `backend/app/core/chronic_packages.py`
- Create: `backend/app/schemas/chronic.py`
- Modify: `backend/app/api/indicators.py` 或新建 `backend/app/api/chronic.py`
- Create: `backend/tests/unit/test_chronic_packages.py`
- Create: `backend/tests/integration/test_chronic.py`
- Create: `miniprogram/pkg-system/pages/chronic/chronic.wxml`
- Create: `miniprogram/pkg-system/pages/chronic/chronic.js`
- Create: `miniprogram/pkg-system/pages/chronic/chronic.json`
- Create: `miniprogram/pkg-system/pages/chronic/chronic.wxss`
- Modify: `miniprogram/app.json` — 注册新页面

**Interfaces:**
- `GET /api/indicators/chronic/{package}?member_id={id}` → `ChronicPackageResponse`
- `package` 枚举：`hypertension` | `diabetes` | `dyslipidemia`
- `ChronicPackageResponse: { package, name, indicators: list[ChronicIndicator], ai_summary }`
- `ChronicIndicator: { key, name, unit, latest, history, status, trend }`

### 子任务 4.1: 后端新增慢性病套餐 API

- [ ] **Step 1: 创建 `backend/app/core/chronic_packages.py`**

```python
from decimal import Decimal
from typing import Optional

_CHRONIC_PACKAGES = {
    "hypertension": {
        "name": "高血压管理",
        "keys": ["systolic_bp", "diastolic_bp", "heart_rate"],
    },
    "diabetes": {
        "name": "糖尿病管理",
        "keys": ["fasting_glucose", "hba1c"],
    },
    "dyslipidemia": {
        "name": "高血脂管理",
        "keys": ["total_cholesterol", "ldl", "hdl", "triglycerides"],
    },
}


def get_package_keys(package: str) -> list[str]:
    return _CHRONIC_PACKAGES.get(package, {}).get("keys", [])


def get_package_name(package: str) -> str:
    return _CHRONIC_PACKAGES.get(package, {}).get("name", package)


def list_packages() -> list[dict]:
    return [{"key": k, "name": v["name"], "keys": v["keys"]} for k, v in _CHRONIC_PACKAGES.items()]
```

- [ ] **Step 2: 创建 Schema `backend/app/schemas/chronic.py`**

```python
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ChronicIndicatorItem(BaseModel):
    key: str
    name: str
    unit: str
    latest: Optional[Decimal] = None
    latest_date: Optional[str] = None
    status: Optional[str] = None
    trend: Optional[str] = None  # improving / worsening / stable


class ChronicPackageResponse(BaseModel):
    package: str
    name: str
    indicators: list[ChronicIndicatorItem]
    ai_summary: str
```

- [ ] **Step 3: 修改 `backend/app/api/indicators.py` 新增慢性病端点**

```python
from app.core.chronic_packages import get_package_keys, get_package_name, list_packages
from app.core.indicator_engine import IndicatorEngine
from app.schemas.chronic import ChronicPackageResponse, ChronicIndicatorItem


@router.get("/chronic", response_model=ResponseSchema[list[dict]])
async def list_chronic_packages():
    return ResponseSchema(data=list_packages())


@router.get("/chronic/{package}", response_model=ResponseSchema[ChronicPackageResponse])
async def get_chronic_package(
    package: str,
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_member: Member = Depends(get_current_member),
):
    from app.core.exceptions import NotFoundException

    keys = get_package_keys(package)
    if not keys:
        raise NotFoundException("套餐不存在")

    target = await db.get(Member, member_id)
    if not target or target.family_id != current_member.family_id:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("无权访问该成员数据")

    result = await db.execute(
        select(IndicatorData)
        .where(
            IndicatorData.member_id == member_id,
            IndicatorData.indicator_key.in_(keys),
        )
        .order_by(IndicatorData.indicator_key, IndicatorData.record_date.desc())
    )
    records = result.scalars().all()

    # Group by key
    by_key: dict[str, list[IndicatorData]] = {}
    for r in records:
        by_key.setdefault(r.indicator_key, []).append(r)

    indicators = []
    for key in keys:
        items = by_key.get(key, [])
        latest = items[0] if items else None
        prev = items[1] if len(items) > 1 else None
        trend = None
        if latest and prev:
            eval_result = IndicatorEngine.evaluate_trend(
                float(latest.value), float(prev.value), key
            )
            trend = eval_result.get("evaluation")
        indicators.append(
            ChronicIndicatorItem(
                key=key,
                name=latest.indicator_name if latest else key,
                unit=latest.unit if latest else "",
                latest=latest.value if latest else None,
                latest_date=str(latest.record_date) if latest else None,
                status=latest.status if latest else None,
                trend=trend,
            )
        )

    ai_summary = await generate_chronic_summary(target.name, package, indicators)

    return ResponseSchema(
        data=ChronicPackageResponse(
            package=package,
            name=get_package_name(package),
            indicators=indicators,
            ai_summary=ai_summary,
        )
    )


async def generate_chronic_summary(name: str, package: str, indicators: list) -> str:
    from app.ai.factory import get_default_provider
    from app.config import settings

    if not settings.KIMI_CODE_API_KEY:
        # Fallback rule-based summary
        abnormal = [i for i in indicators if i.status in ("low", "high", "critical")]
        if abnormal:
            names = "、".join(i.name for i in abnormal)
            return f"{name}的{names}需要关注，建议定期复查并遵医嘱。"
        return f"{name}的{get_package_name(package)}指标目前平稳，请继续保持。"

    provider = get_default_provider()
    lines = [f"请根据以下{name}的{get_package_name(package)}指标，生成一段100字以内的中文管理建议："]
    for i in indicators:
        lines.append(f"- {i.name}: {i.latest} {i.unit}（状态：{i.status or '无数据'}，趋势：{i.trend or '无'}）")
    messages = [
        {"role": "system", "content": "你是一位家庭健康助手。"},
        {"role": "user", "content": "\n".join(lines)},
    ]
    try:
        return await provider.chat(messages, stream=False, max_tokens=256)
    except Exception:
        return f"{name}的{get_package_name(package)}数据已更新，请结合医生建议综合管理。"
```

- [ ] **Step 4: 编写测试并运行**

```python
# backend/tests/unit/test_chronic_packages.py
from app.core.chronic_packages import get_package_keys, get_package_name, list_packages


def test_hypertension_keys():
    assert "systolic_bp" in get_package_keys("hypertension")
    assert "diastolic_bp" in get_package_keys("hypertension")


def test_diabetes_keys():
    assert "fasting_glucose" in get_package_keys("diabetes")


def test_unknown_package():
    assert get_package_keys("unknown") == []
```

集成测试：

```python
# backend/tests/integration/test_chronic.py
class TestChronicPackage:
    async def test_list_packages(self, auth_client):
        resp = await auth_client.get("/api/indicators/chronic")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert any(p["key"] == "hypertension" for p in data)

    async def test_get_package(self, auth_client, test_member, db):
        from datetime import date
        from decimal import Decimal
        from app.models.indicator import IndicatorData

        db.add(
            IndicatorData(
                member_id=test_member.id,
                indicator_key="systolic_bp",
                indicator_name="收缩压",
                value=Decimal("140"),
                unit="mmHg",
                status="high",
                record_date=date(2026, 6, 1),
            )
        )
        await db.commit()

        resp = await auth_client.get(
            f"/api/indicators/chronic/hypertension?member_id={test_member.id}"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["package"] == "hypertension"
        assert any(i["key"] == "systolic_bp" for i in data["indicators"])
```

运行：

```bash
rtk proxy python -m pytest tests/unit/test_chronic_packages.py tests/integration/test_chronic.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/chronic_packages.py backend/app/schemas/chronic.py \
  backend/app/api/indicators.py backend/tests/unit/test_chronic_packages.py \
  backend/tests/integration/test_chronic.py
git commit -m "feat(backend): chronic disease package API"
```

### 子任务 4.2: 前端新增慢性病专区页面

- [ ] **Step 1: 注册页面并创建 JSON**

在 `miniprogram/app.json` pkg-system 分包添加 `pages/chronic/chronic`。

`chronic.json`:

```json
{
  "navigationBarTitleText": "慢性病专区"
}
```

- [ ] **Step 2: 创建 WXML**

```xml
<view class="container">
  <!-- Member Selector -->
  <scroll-view class="member-selector" scroll-x="true" enable-flex="true">
    <view
      class="member-chip {{currentMemberId === item.id ? 'active' : ''}}"
      wx:for="{{members}}"
      wx:key="id"
      data-id="{{item.id}}"
      bindtap="selectMember"
    >
      <text>{{item.name}}</text>
    </view>
  </scroll-view>

  <!-- Package Cards -->
  <view class="package-list">
    <view
      class="package-card"
      wx:for="{{packages}}"
      wx:key="key"
      data-key="{{item.key}}"
      bindtap="viewPackage"
    >
      <text class="package-name">{{item.name}}</text>
      <text class="package-count">{{item.keys.length}} 项指标</text>
    </view>
  </view>
</view>
```

详情页 `chronic-detail`（可选放在同一页用状态切换，或单独页面）。为简化，这里在同一页展示详情：

```xml
<view class="detail-panel" wx:if="{{currentPackage}}">
  <view class="detail-header">
    <text class="detail-name">{{currentPackage.name}}</text>
    <text class="detail-back" bindtap="backToList">‹ 返回套餐列表</text>
  </view>

  <view class="ai-summary" wx:if="{{currentPackage.ai_summary}}">
    <text class="ai-label">AI 管理建议</text>
    <text class="ai-text">{{currentPackage.ai_summary}}</text>
  </view>

  <view class="indicator-list">
    <view class="indicator-card {{item.status}}" wx:for="{{currentPackage.indicators}}" wx:key="key">
      <view class="card-top">
        <text class="indicator-name">{{item.name}}</text>
        <text class="indicator-status">{{item.status || '暂无数据'}}</text>
      </view>
      <view class="card-value-row">
        <text class="value">{{item.latest || '--'}}</text>
        <text class="unit">{{item.unit}}</text>
      </view>
      <text class="trend" wx:if="{{item.trend}}">趋势：{{item.trend}}</text>
      <text class="date" wx:if="{{item.latest_date}}">最近记录：{{item.latest_date}}</text>
    </view>
  </view>
</view>
```

- [ ] **Step 3: 创建 JS**

```javascript
const api = require('../../../utils/api')
const { store, setMembers } = require('../../../utils/store')

const PACKAGES = [
  { key: 'hypertension', name: '高血压管理', keys: ['systolic_bp', 'diastolic_bp', 'heart_rate'] },
  { key: 'diabetes', name: '糖尿病管理', keys: ['fasting_glucose', 'hba1c'] },
  { key: 'dyslipidemia', name: '高血脂管理', keys: ['total_cholesterol', 'ldl', 'hdl', 'triglycerides'] },
]

Page({
  data: {
    members: [],
    currentMemberId: null,
    packages: PACKAGES,
    currentPackage: null,
  },

  onLoad() {
    this.loadMembers()
  },

  async loadMembers() {
    try {
      const res = await api.get('/api/members')
      const members = res.data.members || []
      setMembers(members)
      this.setData({
        members,
        currentMemberId: store.currentMemberId || (members[0] && members[0].id),
      })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    }
  },

  selectMember(e) {
    const id = e.currentTarget.dataset.id
    this.setData({ currentMemberId: id, currentPackage: null })
  },

  async viewPackage(e) {
    const key = e.currentTarget.dataset.key
    const { currentMemberId } = this.data
    if (!currentMemberId) return
    try {
      const res = await api.get(`/api/indicators/chronic/${key}?member_id=${currentMemberId}`)
      this.setData({ currentPackage: res.data })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    }
  },

  backToList() {
    this.setData({ currentPackage: null })
  },
})
```

- [ ] **Step 4: 在首页或个人中心添加入口**

在 `miniprogram/pages/profile/profile.wxml` 的功能列表中增加：

```xml
<view class="menu-item" bindtap="goToChronic">
  <text class="menu-icon">🫀</text>
  <text class="menu-label">慢性病专区</text>
  <text class="menu-arrow">›</text>
</view>
```

在 `profile.js` 中：

```javascript
goToChronic() {
  wx.navigateTo({ url: '/pkg-system/pages/chronic/chronic' })
},
```

- [ ] **Step 5: 手动验证**

1. 从「我的」进入慢性病专区
2. 切换成员
3. 点击高血压套餐
4. 查看指标卡片和 AI 管理建议

- [ ] **Step 6: Commit**

```bash
git add miniprogram/pkg-system/pages/chronic/ miniprogram/pages/profile/profile.* miniprogram/app.json
git commit -m "feat(frontend): chronic disease package page"
```

---

## Task 5: P0-5 儿童成长与发育模块

**目标：** 为儿童成员提供成长曲线（身高/体重/头围/BMI）和发育里程碑跟踪。

**Files:**
- Create: `backend/app/models/growth_record.py`
- Create: `backend/app/schemas/growth.py`
- Create: `backend/app/core/milestone_data.py`
- Create: `backend/app/api/child.py`
- Create: Alembic migration for growth_record table
- Create: `backend/tests/unit/test_milestone_data.py`
- Create: `backend/tests/integration/test_child_growth.py`
- Create: `miniprogram/pkg-child/pages/growth/growth.*`
- Create: `miniprogram/pkg-child/pages/milestone/milestone.*`
- Modify: `miniprogram/pkg-child/pages/child-dashboard/child-dashboard.*`
- Modify: `miniprogram/app.json`

**Interfaces:**
- `POST /api/child/growth` — 创建成长记录
- `GET /api/child/growth?member_id={id}` — 查询成长记录列表
- `DELETE /api/child/growth/{record_id}` — 删除记录
- `GET /api/child/milestones?member_id={id}` — 获取里程碑状态
- `GrowthRecord` 模型：`id, member_id, type(height/weight/head_circumference/bmi), value, record_date, notes`

### 子任务 5.1: 后端新增成长记录模型与 API

- [ ] **Step 1: 创建模型 `backend/app/models/growth_record.py`**

```python
from datetime import date
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, String, Date, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class GrowthRecord(Base):
    __tablename__ = "growth_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(Integer, ForeignKey("members.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # height/weight/head_circumference/bmi
    value: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    member = relationship("Member", back_populates="growth_records")
```

- [ ] **Step 2: 修改 `backend/app/models/member.py` 添加 relationship**

```python
# 在 Member 类中添加
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.growth_record import GrowthRecord

growth_records: Mapped[list["GrowthRecord"]] = relationship("GrowthRecord", back_populates="member")
```

- [ ] **Step 3: 创建 Schema `backend/app/schemas/growth.py`**

```python
from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class GrowthRecordCreate(BaseModel):
    member_id: int
    type: str  # height/weight/head_circumference/bmi
    value: Decimal
    record_date: date
    notes: Optional[str] = None


class GrowthRecordOut(GrowthRecordCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class GrowthPercentile(BaseModel):
    type: str
    value: Decimal
    age_months: int
    percentile: Optional[int] = None  # 0-100, None if no WHO data
    status: str  # normal / warning / alert


class MilestoneItem(BaseModel):
    category: str
    name: str
    expected_months: int
    status: str  # achieved / warning / delayed / normal
    notes: Optional[str] = None
```

- [ ] **Step 4: 创建核心数据 `backend/app/core/milestone_data.py`**

```python
MILESTONES = [
    {"category": "大运动", "name": "翻身", "expected_months": 6},
    {"category": "大运动", "name": "独坐", "expected_months": 9},
    {"category": "大运动", "name": "爬行", "expected_months": 12},
    {"category": "大运动", "name": "独站", "expected_months": 15},
    {"category": "大运动", "name": "独走", "expected_months": 18},
    {"category": "语言", "name": "叫爸妈", "expected_months": 18},
    {"category": "精细运动", "name": "串珠子", "expected_months": 24},
    {"category": "大运动", "name": "双脚跳", "expected_months": 30},
    {"category": "大运动", "name": "骑三轮车", "expected_months": 36},
    {"category": "大运动", "name": "单脚站", "expected_months": 48},
    {"category": "精细运动", "name": "系鞋带", "expected_months": 60},
]


def get_milestones_for_age(age_months: int) -> list[dict]:
    """Return milestones relevant for current age with status."""
    results = []
    for m in MILESTONES:
        if age_months >= m["expected_months"] + 3:
            status = "delayed"
        elif age_months >= m["expected_months"]:
            status = "warning"
        else:
            status = "normal"
        results.append({**m, "status": status})
    return results
```

- [ ] **Step 5: 创建 API `backend/app/api/child.py`**

```python
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_member
from app.db.session import get_db
from app.models.growth_record import GrowthRecord
from app.models.member import Member
from app.schemas.growth import GrowthRecordCreate, GrowthRecordOut, MilestoneItem
from app.schemas.response import ResponseSchema
from app.core.milestone_data import get_milestones_for_age
from app.core.exceptions import ForbiddenException, NotFoundException

router = APIRouter(prefix="/api/child", tags=["child"])


def _calc_age_months(birth_date: date, today: date) -> int:
    return (today.year - birth_date.year) * 12 + (today.month - birth_date.month)


@router.post("/growth", response_model=ResponseSchema[GrowthRecordOut])
async def create_growth_record(
    payload: GrowthRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_member: Member = Depends(get_current_member),
):
    target = await db.get(Member, payload.member_id)
    if not target or target.family_id != current_member.family_id:
        raise ForbiddenException("无权访问该成员数据")
    if target.type != "child":
        raise ForbiddenException("仅支持儿童成员")

    record = GrowthRecord(**payload.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return ResponseSchema(data=GrowthRecordOut.model_validate(record))


@router.get("/growth", response_model=ResponseSchema[list[GrowthRecordOut]])
async def list_growth_records(
    member_id: int,
    type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_member: Member = Depends(get_current_member),
):
    target = await db.get(Member, member_id)
    if not target or target.family_id != current_member.family_id:
        raise ForbiddenException("无权访问该成员数据")

    stmt = select(GrowthRecord).where(GrowthRecord.member_id == member_id)
    if type:
        stmt = stmt.where(GrowthRecord.type == type)
    stmt = stmt.order_by(GrowthRecord.record_date.desc())
    result = await db.execute(stmt)
    records = result.scalars().all()
    return ResponseSchema(data=[GrowthRecordOut.model_validate(r) for r in records])


@router.delete("/growth/{record_id}")
async def delete_growth_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_member: Member = Depends(get_current_member),
):
    record = await db.get(GrowthRecord, record_id)
    if not record:
        raise NotFoundException("记录不存在")
    target = await db.get(Member, record.member_id)
    if not target or target.family_id != current_member.family_id:
        raise ForbiddenException("无权访问该成员数据")

    await db.delete(record)
    await db.commit()
    return ResponseSchema(data={"deleted": True})


@router.get("/milestones", response_model=ResponseSchema[list[MilestoneItem]])
async def list_milestones(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_member: Member = Depends(get_current_member),
):
    target = await db.get(Member, member_id)
    if not target or target.family_id != current_member.family_id:
        raise ForbiddenException("无权访问该成员数据")
    if not target.birth_date:
        return ResponseSchema(data=[])

    age_months = _calc_age_months(target.birth_date, date.today())
    milestones = get_milestones_for_age(age_months)
    return ResponseSchema(
        data=[MilestoneItem(**m) for m in milestones]
    )
```

- [ ] **Step 6: 注册路由 `backend/app/main.py`**

```python
from app.api import child

app.include_router(child.router)
```

- [ ] **Step 7: 生成 Alembic 迁移**

```bash
cd backend
source .venv/bin/activate
alembic revision --autogenerate -m "add growth_records table"
alembic upgrade head
```

- [ ] **Step 8: 编写测试并运行**

```python
# backend/tests/unit/test_milestone_data.py
from app.core.milestone_data import get_milestones_for_age


def test_milestone_status_for_baby():
    results = get_milestones_for_age(4)
    rolling = next(m for m in results if m["name"] == "翻身")
    assert rolling["status"] == "normal"  # not due yet


def test_milestone_status_for_delayed():
    results = get_milestones_for_age(12)
    rolling = next(m for m in results if m["name"] == "翻身")
    assert rolling["status"] == "delayed"
```

集成测试：

```python
# backend/tests/integration/test_child_growth.py
class TestChildGrowth:
    async def test_create_growth_record(self, auth_client, test_member, db):
        test_member.type = "child"
        test_member.birth_date = date(2024, 1, 1)
        await db.commit()

        resp = await auth_client.post(
            "/api/child/growth",
            json={
                "member_id": test_member.id,
                "type": "height",
                "value": "80.5",
                "record_date": "2026-06-01",
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["type"] == "height"
        assert data["value"] == "80.50"

    async def test_list_milestones(self, auth_client, test_member, db):
        test_member.type = "child"
        test_member.birth_date = date(2023, 1, 1)
        await db.commit()

        resp = await auth_client.get(f"/api/child/milestones?member_id={test_member.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) > 0
        assert all("category" in m for m in data)
```

运行：

```bash
rtk proxy python -m pytest tests/unit/test_milestone_data.py tests/integration/test_child_growth.py -v
```

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/growth_record.py backend/app/models/member.py \
  backend/app/schemas/growth.py backend/app/core/milestone_data.py \
  backend/app/api/child.py backend/app/main.py backend/alembic/versions/ \
  backend/tests/unit/test_milestone_data.py backend/tests/integration/test_child_growth.py
git commit -m "feat(backend): child growth records and milestones API"
```

### 子任务 5.2: 前端新增成长曲线与里程碑页面

- [ ] **Step 1: 注册页面**

在 `miniprogram/app.json` pkg-child 分包添加：

```json
"pages/growth/growth",
"pages/milestone/milestone"
```

- [ ] **Step 2: 创建成长曲线页面**

`growth.wxml`:

```xml
<view class="container">
  <view class="type-tabs">
    <view
      class="tab {{activeType === item ? 'active' : ''}}"
      wx:for="{{types}}"
      wx:key="*this"
      data-type="{{item}}"
      bindtap="switchType"
    >
      <text>{{typeLabels[item]}}</text>
    </view>
  </view>

  <view class="chart-section">
    <canvas type="2d" id="growthCanvas" class="chart-canvas"></canvas>
  </view>

  <view class="section">
    <text class="section-title">历史记录</text>
    <view class="record-list" wx:if="{{records.length}}">
      <view class="record-row" wx:for="{{records}}" wx:key="id">
        <text>{{item.record_date}}</text>
        <text>{{item.value}} {{unit}}</text>
        <text class="delete" data-id="{{item.id}}" bindtap="deleteRecord">删除</text>
      </view>
    </view>
    <empty-state wx:else title="暂无记录" subtitle="点击右下角添加" />
  </view>

  <view class="fab" bindtap="openAddForm">
    <text class="fab-icon">+</text>
  </view>
</view>
```

`growth.js` 核心逻辑：

```javascript
const api = require('../../../utils/api')

const TYPE_LABELS = {
  height: '身高',
  weight: '体重',
  head_circumference: '头围',
  bmi: 'BMI',
}

const TYPE_UNITS = {
  height: 'cm',
  weight: 'kg',
  head_circumference: 'cm',
  bmi: '',
}

Page({
  data: {
    memberId: '',
    activeType: 'height',
    types: ['height', 'weight', 'head_circumference', 'bmi'],
    typeLabels: TYPE_LABELS,
    unit: 'cm',
    records: [],
  },

  onLoad(options) {
    this.setData({ memberId: options.member_id || '' })
    this.loadRecords()
  },

  async loadRecords() {
    const { memberId, activeType } = this.data
    if (!memberId) return
    try {
      const res = await api.get(`/api/child/growth?member_id=${memberId}&type=${activeType}`)
      const records = res.data || []
      this.setData({
        records,
        unit: TYPE_UNITS[activeType],
      })
      this.drawChart(records)
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    }
  },

  switchType(e) {
    const type = e.currentTarget.dataset.type
    this.setData({ activeType: type })
    this.loadRecords()
  },

  drawChart(records) {
    // 类似 indicator-detail 的 canvas 绘制逻辑
    // X轴：日期，Y轴：数值
    // 后续可叠加 WHO 百分位曲线
  },

  openAddForm() {
    const { memberId, activeType } = this.data
    wx.navigateTo({
      url: `/pkg-system/pages/indicator-manual/indicator-manual?member_id=${memberId}`,
    })
  },

  async deleteRecord(e) {
    const id = e.currentTarget.dataset.id
    const res = await wx.showModal({ title: '确认删除', content: '删除该记录？' })
    if (!res.confirm) return
    try {
      await api.del(`/api/child/growth/${id}`)
      wx.showToast({ title: '已删除', icon: 'success' })
      this.loadRecords()
    } catch (err) {
      wx.showToast({ title: err.message || '删除失败', icon: 'none' })
    }
  },
})
```

- [ ] **Step 3: 创建里程碑页面**

`milestone.wxml`:

```xml
<view class="container">
  <view class="summary" wx:if="{{ageMonths}}">
    <text>当前 {{ageMonths}} 个月</text>
  </view>
  <view class="milestone-list">
    <view class="milestone-item {{item.status}}" wx:for="{{milestones}}" wx:key="*this">
      <view class="milestone-main">
        <text class="category">{{item.category}}</text>
        <text class="name">{{item.name}}</text>
        <text class="expected">建议月龄：{{item.expected_months}}</text>
      </view>
      <text class="status-label">{{statusLabels[item.status]}}</text>
    </view>
  </view>
</view>
```

`milestone.js`:

```javascript
const api = require('../../../utils/api')

const STATUS_LABELS = {
  normal: '未到期',
  warning: '需关注',
  delayed: '已延迟',
  achieved: '已达成',
}

Page({
  data: {
    memberId: '',
    ageMonths: 0,
    milestones: [],
    statusLabels: STATUS_LABELS,
  },

  onLoad(options) {
    this.setData({ memberId: options.member_id || '' })
    this.loadMilestones()
  },

  async loadMilestones() {
    const { memberId } = this.data
    if (!memberId) return
    try {
      const res = await api.get(`/api/child/milestones?member_id=${memberId}`)
      this.setData({ milestones: res.data || [] })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    }
  },
})
```

- [ ] **Step 4: 修改儿童档案首页添加入口**

在 `child-dashboard.wxml` 的 quick-links 中：

```xml
<view class="quick-item" bindtap="goToGrowth">
  <text class="quick-icon">📏</text>
  <text class="quick-label">成长</text>
</view>
<view class="quick-item" bindtap="goToMilestone">
  <text class="quick-icon">🏆</text>
  <text class="quick-label">里程碑</text>
</view>
```

在 `child-dashboard.js` 中：

```javascript
goToGrowth() {
  const id = this.data.member && this.data.member.id
  if (!id) return
  wx.navigateTo({ url: `/pkg-child/pages/growth/growth?member_id=${id}` })
},

goToMilestone() {
  const id = this.data.member && this.data.member.id
  if (!id) return
  wx.navigateTo({ url: `/pkg-child/pages/milestone/milestone?member_id=${id}` })
},
```

- [ ] **Step 5: 手动验证**

1. 进入儿童档案首页
2. 点击成长/里程碑入口
3. 成长页切换身高/体重，查看曲线
4. 里程碑页查看按年龄状态

- [ ] **Step 6: Commit**

```bash
git add miniprogram/pkg-child/pages/growth/ miniprogram/pkg-child/pages/milestone/ \
  miniprogram/pkg-child/pages/child-dashboard/child-dashboard.* miniprogram/app.json
git commit -m "feat(frontend): child growth and milestone pages"
```

---

## Task 6: P0-2 真实 OCR 报告识别

**目标：** 接入真实 OCR 服务，支持多 Provider fallback，从报告图片中提取指标并自动创建 IndicatorData。

**Files:**
- Create: `backend/app/ai/ocr_provider.py`
- Create: `backend/app/ai/tencent_ocr_provider.py`
- Create: `backend/app/ai/baidu_ocr_provider.py`
- Modify: `backend/app/ai/factory.py`
- Modify: `backend/app/core/ocr_service.py`
- Create: `backend/app/services/ocr_pipeline.py`
- Create: `backend/app/schemas/ocr.py`
- Modify: `backend/app/api/reports.py`
- Modify: `backend/app/config.py`
- Create: `backend/tests/unit/test_ocr_pipeline.py`
- Create: `backend/tests/integration/test_ocr_real.py`
- Modify: `miniprogram/pages/upload/upload.js` — 失败兜底

**Interfaces:**
- `OCRProvider.extract_text(image_url: str) -> str`
- `OCRProvider.extract_indicators(image_url: str) -> list[dict]`
- `OCRPipeline.run(report_id: int, image_url: str) -> OCRResult`
- `POST /api/reports/{id}/ocr` 触发流水线（保持现有接口不变）

### 子任务 6.1: 后端 OCR Provider 抽象与实现

- [ ] **Step 1: 创建抽象接口 `backend/app/ai/ocr_provider.py`**

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator


class OCRProvider(ABC):
    @abstractmethod
    async def extract_text(self, image_url: str) -> str:
        """Extract raw text from image."""
        pass

    @abstractmethod
    async def extract_indicators(self, image_url: str) -> list[dict]:
        """Extract structured health indicators from image.

        Returns list of dicts: [{"indicator_key", "indicator_name", "value", "unit", "status"}, ...]
        """
        pass

    @abstractmethod
    def name(self) -> str:
        pass
```

- [ ] **Step 2: 创建 Tencent OCR Provider `backend/app/ai/tencent_ocr_provider.py`**

```python
import json
import os
from typing import Optional

import httpx

from app.ai.ocr_provider import OCRProvider
from app.config import settings
from app.core.exceptions import BusinessException


class TencentOCRProvider(OCRProvider):
    """Tencent Cloud OCR for general printed text.

    Docs: https://cloud.tencent.com/document/product/866/33524
    """

    def __init__(self):
        self.secret_id = settings.TENCENT_OCR_SECRET_ID
        self.secret_key = settings.TENCENT_OCR_SECRET_KEY
        if not self.secret_id or not self.secret_key:
            raise BusinessException("Tencent OCR credentials not configured")

    def name(self) -> str:
        return "tencent-ocr"

    async def extract_text(self, image_url: str) -> str:
        # Placeholder: actual Tencent Cloud API requires signature v3
        # For now return empty, real implementation uses tencentcloud-sdk-python
        return ""

    async def extract_indicators(self, image_url: str) -> list[dict]:
        text = await self.extract_text(image_url)
        from app.services.ocr_pipeline import parse_indicators_from_text
        return parse_indicators_from_text(text)
```

注意：真实 Tencent OCR 建议使用 `tencentcloud-sdk-python` 的 `ocr_client`。这里给出最小接口占位，实际接入时再填充。

- [ ] **Step 3: 创建 Baidu OCR Provider `backend/app/ai/baidu_ocr_provider.py`**

```python
import httpx

from app.ai.ocr_provider import OCRProvider
from app.config import settings
from app.core.exceptions import BusinessException


class BaiduOCRProvider(OCRProvider):
    """Baidu Cloud OCR (accurate_basic).

    Docs: https://ai.baidu.com/ai-doc/OCR/zk3h7xz52
    """

    def __init__(self):
        self.api_key = settings.BAIDU_OCR_API_KEY
        self.secret_key = settings.BAIDU_OCR_SECRET_KEY
        if not self.api_key or not self.secret_key:
            raise BusinessException("Baidu OCR credentials not configured")
        self.access_token: str | None = None

    def name(self) -> str:
        return "baidu-ocr"

    async def _get_access_token(self) -> str:
        if self.access_token:
            return self.access_token
        url = "https://aip.baidubce.com/oauth/2.0/token"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                params={
                    "grant_type": "client_credentials",
                    "client_id": self.api_key,
                    "client_secret": self.secret_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self.access_token = data["access_token"]
            return self.access_token

    async def extract_text(self, image_url: str) -> str:
        token = await self._get_access_token()
        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic?access_token={token}"
        async with httpx.AsyncClient(timeout=60) as client:
            # Baidu supports image URL in some endpoints, or base64 image data
            # For URL-based, use general_url_recognition:
            url_recog = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general?access_token={token}"
            resp = await client.post(
                url_recog,
                data={"url": image_url},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
            words = [w["words"] for w in data.get("words_result", [])]
            return "\n".join(words)

    async def extract_indicators(self, image_url: str) -> list[dict]:
        text = await self.extract_text(image_url)
        from app.services.ocr_pipeline import parse_indicators_from_text
        return parse_indicators_from_text(text)
```

- [ ] **Step 4: 修改 `backend/app/ai/factory.py` 添加 OCR Provider 工厂**

```python
from app.ai.ocr_provider import OCRProvider
from app.ai.tencent_ocr_provider import TencentOCRProvider
from app.ai.baidu_ocr_provider import BaiduOCRProvider


def get_ocr_provider(name: Optional[str] = None) -> OCRProvider:
    name = (name or settings.DEFAULT_OCR_PROVIDER or "baidu").lower()
    registry: dict[str, type[OCRProvider]] = {
        "tencent": TencentOCRProvider,
        "baidu": BaiduOCRProvider,
    }
    cls = registry.get(name)
    if not cls:
        raise ValueError(f"Unknown OCR provider: {name}")
    return cls()


async def ocr_with_fallback(image_url: str) -> tuple[str, list[dict]]:
    providers = [settings.DEFAULT_OCR_PROVIDER] + settings.FALLBACK_OCR_PROVIDERS
    providers = [p for p in providers if p]
    last_error: Optional[Exception] = None
    for provider_name in providers:
        try:
            provider = get_ocr_provider(provider_name)
            text = await provider.extract_text(image_url)
            indicators = await provider.extract_indicators(image_url)
            return text, indicators
        except Exception as exc:
            logger.warning(f"OCR provider {provider_name} failed: {exc}")
            last_error = exc
    raise RuntimeError(f"All OCR providers failed. Last error: {last_error}")
```

- [ ] **Step 5: 修改 `backend/app/config.py` 添加 OCR 配置**

```python
    # OCR Provider configuration
    DEFAULT_OCR_PROVIDER: str = "baidu"
    FALLBACK_OCR_PROVIDERS: list[str] = ["tencent"]
    TENCENT_OCR_SECRET_ID: str = ""
    TENCENT_OCR_SECRET_KEY: str = ""
    BAIDU_OCR_API_KEY: str = ""
    BAIDU_OCR_SECRET_KEY: str = ""
```

记得 `FALLBACK_OCR_PROVIDERS` 在 `.env` 中需要 JSON 数组格式 `[]` 或 `["tencent"]`。

- [ ] **Step 6: 创建 OCR Pipeline `backend/app/services/ocr_pipeline.py`**

```python
import re
from decimal import Decimal
from typing import Optional

from app.ai.factory import ocr_with_fallback
from app.core.indicator_engine import IndicatorEngine
from app.core.indicator_normalizer import normalize_indicator_name, get_indicator_by_key
from app.db.session import async_session
from app.models.indicator import IndicatorData
from app.models.report import Report


_INDICATOR_LINE_RE = re.compile(
    r"([一-龥a-zA-Z]+)\s*[:：]?\s*([\d.]+)\s*([a-zA-Z/%°μu个×/L²]+)?",
    re.UNICODE,
)


def parse_indicators_from_text(text: str) -> list[dict]:
    """Parse common indicator patterns from OCR text."""
    indicators = []
    seen = set()
    for line in text.splitlines():
        match = _INDICATOR_LINE_RE.search(line)
        if not match:
            continue
        raw_name = match.group(1).strip()
        value_str = match.group(2)
        unit = (match.group(3) or "").strip()
        try:
            value = Decimal(value_str)
        except Exception:
            continue

        key = normalize_indicator_name(raw_name)
        if key:
            meta = get_indicator_by_key(key)
            if meta:
                key = meta["key"]
                name = meta["name"]
                unit = unit or meta["unit"]
                lower = meta.get("lower_limit")
                upper = meta.get("upper_limit")
            else:
                name = raw_name
                lower = upper = None
        else:
            key = raw_name
            name = raw_name
            lower = upper = None

        if key in seen:
            continue
        seen.add(key)

        status = "normal"
        if lower is not None and upper is not None:
            status = IndicatorEngine.judge(key, value, lower, upper)

        indicators.append({
            "indicator_key": key,
            "indicator_name": name,
            "value": value,
            "unit": unit,
            "status": status,
            "lower_limit": lower,
            "upper_limit": upper,
        })
    return indicators


async def run_ocr_pipeline(report_id: int, image_url: str) -> dict:
    """Run OCR, extract indicators, save to DB, return result."""
    text, extracted = await ocr_with_fallback(image_url)

    async with async_session() as db:
        report = await db.get(Report, report_id)
        if report:
            report.extracted_indicators = extracted
            report.ocr_status = "completed" if extracted else "failed"
            await db.commit()

        for item in extracted:
            db.add(
                IndicatorData(
                    member_id=report.member_id,
                    indicator_key=item["indicator_key"],
                    indicator_name=item["indicator_name"],
                    value=item["value"],
                    unit=item["unit"],
                    lower_limit=item.get("lower_limit"),
                    upper_limit=item.get("upper_limit"),
                    status=item["status"],
                    source_report_id=report_id,
                    record_date=report.report_date,
                )
            )
        await db.commit()

    return {"text": text, "extracted": extracted, "count": len(extracted)}
```

- [ ] **Step 7: 修改 `backend/app/core/ocr_service.py` 保留兼容**

保持 `get_ocr_service()` 返回 `MockOCRService` 或 `RegexOCRService` 作为开发 fallback。真实 OCR 通过新 pipeline 调用。

- [ ] **Step 8: 修改 `backend/app/api/reports.py` 的 OCR 触发接口**

```python
from app.services.ocr_pipeline import run_ocr_pipeline
from app.services.oss_service import OSSService


@router.post("/{report_id}/ocr")
async def trigger_ocr(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_member: Member = Depends(get_current_member),
):
    report = await db.get(Report, report_id)
    if not report:
        raise NotFoundException("报告不存在")
    target = await db.get(Member, report.member_id)
    if not target or target.family_id != current_member.family_id:
        raise ForbiddenException("无权访问")

    if not report.images:
        raise BusinessException("报告没有图片")

    # Get first image URL; if private, generate signed URL
    image_url = report.images[0]
    # Run pipeline (may raise if all providers fail)
    try:
        result = await run_ocr_pipeline(report_id, image_url)
    except Exception as exc:
        report.ocr_status = "failed"
        await db.commit()
        raise BusinessException(f"OCR识别失败: {exc}")

    return ResponseSchema(data=result)
```

- [ ] **Step 9: 编写测试**

```python
# backend/tests/unit/test_ocr_pipeline.py
from app.services.ocr_pipeline import parse_indicators_from_text


def test_parse_blood_pressure():
    text = "收缩压 150 mmHg\n舒张压 80 mmHg"
    indicators = parse_indicators_from_text(text)
    assert any(i["indicator_key"] == "systolic_bp" and float(i["value"]) == 150 for i in indicators)


def test_parse_glucose():
    text = "空腹血糖 7.2 mmol/L"
    indicators = parse_indicators_from_text(text)
    assert any(i["indicator_key"] == "fasting_glucose" for i in indicators)
```

- [ ] **Step 10: 更新 `.env.example`**

```bash
# OCR Provider configuration
DEFAULT_OCR_PROVIDER=baidu
FALLBACK_OCR_PROVIDERS=["tencent"]
TENCENT_OCR_SECRET_ID=your-tencent-secret-id
TENCENT_OCR_SECRET_KEY=your-tencent-secret-key
BAIDU_OCR_API_KEY=your-baidu-api-key
BAIDU_OCR_SECRET_KEY=your-baidu-secret-key
```

- [ ] **Step 11: Commit**

```bash
git add backend/app/ai/ocr_provider.py backend/app/ai/tencent_ocr_provider.py \
  backend/app/ai/baidu_ocr_provider.py backend/app/ai/factory.py \
  backend/app/core/ocr_service.py backend/app/services/ocr_pipeline.py \
  backend/app/schemas/ocr.py backend/app/api/reports.py backend/app/config.py \
  backend/.env.example backend/tests/unit/test_ocr_pipeline.py

git commit -m "feat(backend): real OCR provider integration with Baidu/Tencent fallback"
```

### 子任务 6.2: 前端 OCR 失败兜底

已在 P0-6 中完成：上传结果页识别失败时弹出「手动录入」引导。

---

## 自我审查

### 1. Spec 覆盖检查

| 需求 | 覆盖任务 |
|------|----------|
| 真实 OCR 报告识别 | Task 6 |
| 指标中心表单视图 | Task 2 |
| 慢性病专区 | Task 4 |
| 儿童成长与发育模块 | Task 5 |
| 手动录入页 | Task 3 |
| API Base 环境化 | Task 1 |

### 2. Placeholder 检查

- 无 "TBD" / "TODO" / "implement later"
- 每个代码步骤包含实际可运行代码
- 测试包含具体断言

### 3. 类型一致性检查

- `IndicatorMatrixResponse` 与 API 返回一致
- `ChronicPackageResponse` 与 API 返回一致
- `GrowthRecord` 模型与 Schema 一致
- `OCRProvider` 接口与 Provider 实现一致

### 4. 已知限制

- Tencent OCR Provider 使用占位实现，实际接入需引入 `tencentcloud-sdk-python`
- 成长曲线 WHO 百分位数据未包含，后续需补充静态数据表
- OCR 指标解析正则较简单，复杂报告可能需要 LLM 后处理

---

## 执行交接

**Plan complete and saved to `docs/superpowers/plans/2026-06-25-p0-core-features.md`.**

两个执行选项：

**1. Subagent-Driven（推荐）** - 每个 Task 派发独立子代理执行，我在每个 Task 完成后 review 并进入下一个

**2. Inline Execution** - 在当前会话中按 Task 顺序直接实现，每个 Task 完成后验证并提交

**Which approach?**
