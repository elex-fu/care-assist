# Playwright E2E 测试全面验证方案（方案A）

> 日期：2026-05-16 | 目标：补齐后端 FastAPI 所有 15 个 API 模块的 Playwright E2E 测试，统一基础架构

---

## 1. 目标

1. 补齐 7 个缺失模块的 E2E 测试：auth、export、health_events、home、medications、summary、ws
2. 重构现有 8 个测试文件，消除重复注册/token 获取代码，统一到 `conftest.py` fixtures
3. 建立可维护、可扩展的 E2E 测试基础架构
4. 所有测试覆盖：Swagger 文档存在性验证 + 核心 API 业务流验证

---

## 2. 现有测试状态

| API 模块 | 现有 E2E 文件 | 覆盖状态 |
|----------|-------------|----------|
| ai_conversations | `test_ai_conversation_e2e.py` | Swagger + 创建/消息/删除流 |
| auth | — | **缺失** |
| export | — | **缺失** |
| health_events | — | **缺失** |
| home | — | **缺失** |
| hospitals | `test_hospital_e2e.py` | Swagger + CRUD + watch/compare |
| indicators | `test_indicator_e2e.py` | Swagger + CRUD + batch + trend |
| medications | — | **缺失** |
| members | `test_member_e2e.py` | Swagger + export |
| reminders | `test_timeline_reminder_e2e.py` | 包含在 timeline_reminder 中 |
| reports | `test_report_e2e.py` | Swagger + upload + OCR |
| search | `test_search_e2e.py` | Swagger + query |
| summary | — | **缺失** |
| vaccines | `test_vaccine_e2e.py` | Swagger + CRUD |
| ws | — | **缺失** |

---

## 3. 统一基础架构设计

### 3.1 新增 `backend/e2e/conftest.py`

引入以下 session-scoped fixtures，供所有测试复用：

| Fixture | 作用 | Scope |
|---------|------|-------|
| `playwright` | Playwright 实例启动/关闭 | session |
| `browser` | Chromium 浏览器实例 | session |
| `api_context` | 独立的浏览器 context，用于纯 API 请求 | session |
| `base_url` | 从环境变量读取，默认 `http://localhost:8000` | session |
| `swagger_screenshot_dir` | 截图输出目录 | session |

以及 function-scoped fixtures：

| Fixture | 作用 |
|---------|------|
| `registered_user` | 调用 `/api/auth/register` 注册新用户，返回 `{token, member_id, family_id}` |
| `auth_headers` | 从 `registered_user` 提取的 `Authorization: Bearer <token>` headers |
| `test_member` | 在当前用户家庭下创建第二个成员，用于多成员场景测试 |

### 3.2 公共辅助函数

```python
async def register_user(api_context, base_url, creator_name: str | None = None) -> dict:
    """注册新用户并返回完整用户信息。"""

async def cleanup_user(api_context, base_url, token: str) -> None:
    """测试后清理：删除用户及其家庭数据。"""

async def assert_swagger_has_paths(page, base_url, paths: list[str]) -> None:
    """验证 openapi.json 包含指定 paths，并截图 Swagger UI。"""
```

### 3.3 现有测试改造范围

现有 8 个测试文件中，每份都包含约 20~40 行的重复注册逻辑：

```python
code = f"mock_e2e_{uuid.uuid4().hex[:8]}"
creator_name = "E2E...User"
resp = await context.request.post(
    f"{BASE_URL}/api/auth/register?creator_name={creator_name}",
    headers={"Content-Type": "application/json"},
    data=json.dumps({"code": code}),
)
assert resp.ok
body = await resp.json()
token = body["data"]["access_token"]
member_id = body["data"]["member"]["id"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
```

改造后简化为：

```python
async def test_api_xxx_flow_via_playwright(api_context, base_url, registered_user, auth_headers):
    member_id = registered_user["member_id"]
    # 直接开始业务流测试
```

---

## 4. 缺失模块测试设计

### 4.1 `test_auth_e2e.py`

- `test_swagger_docs_show_auth`
  - 验证 `/api/login`、`/api/register`、`/api/refresh` 存在于 openapi.json
- `test_register_and_login_flow`
  - 注册新用户 → 用同一 code 登录 → 验证返回 token 一致
  - 测试错误 code 返回 401
- `test_refresh_token_flow`
  - 注册 → 获取 refresh_token → 调用 `/api/refresh` → 验证新 access_token 有效
- `test_me_endpoint_with_invalid_token`
  - 携带伪造 token 访问 `/api/members/me`，验证返回 401

### 4.2 `test_export_e2e.py`

- `test_swagger_docs_show_export`
  - 验证 `/api/export/excel`、`/api/export/pdf` 存在于 openapi.json
- `test_export_excel_flow`
  - 注册用户 → 创建指标数据 → 调用 `/api/export/excel?member_id=...`
  - 验证响应头 `Content-Disposition` 包含 `.xlsx`
  - 验证 Content-Type 为 `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- `test_export_pdf_flow`
  - 同上，验证 PDF 导出响应头和 Content-Type
- `test_export_with_date_range`
  - 创建不同日期的指标 → 带 `start_date`、`end_date` 参数导出 → 验证仅返回范围内数据

### 4.3 `test_health_events_e2e.py`

- `test_swagger_docs_show_health_events`
  - 验证 `/api/health-events` CRUD endpoints 存在
- `test_health_event_crud_flow`
  - 创建事件（type=visit）→ 列表查询 → 更新事件 → 删除事件
- `test_health_event_filter_by_type`
  - 创建多种类型事件 → 按 type 过滤 → 验证结果集正确
- `test_health_event_timeline_order`
  - 创建多个不同日期的事件 → 列表查询 → 验证按日期倒序排列

### 4.4 `test_home_e2e.py`

- `test_swagger_docs_show_dashboard`
  - 验证 `/api/dashboard` 存在于 openapi.json
- `test_dashboard_with_empty_data`
  - 注册新用户 → 调用 `/api/dashboard` → 验证返回空状态结构（无异常）
- `test_dashboard_with_data`
  - 注册用户 → 添加成员 → 创建指标和报告 → 调用 `/api/dashboard`
  - 验证返回包含家庭成员数、最新指标、待办提醒等字段

### 4.5 `test_medications_e2e.py`

- `test_swagger_docs_show_medications`
  - 验证 `/api/medications` CRUD + take endpoint 存在
- `test_medication_crud_flow`
  - 创建用药提醒 → 列表查询 → 详情查询 → 更新 → 删除
- `test_medication_take_flow`
  - 创建用药 → 调用 `/api/medications/{id}/take` → 验证服药记录生成
  - 再次查询详情，验证 logs 数组包含新记录
- `test_medication_permission_isolation`
  - 用户A创建用药 → 用户B（不同家庭）尝试访问 → 验证返回 403

### 4.6 `test_summary_e2e.py`

- `test_swagger_docs_show_summary`
  - 验证 `/api/annual` 存在于 openapi.json
- `test_annual_summary_with_data`
  - 注册用户 → 创建跨月份指标 → 调用 `/api/annual`
  - 验证返回包含年度统计、趋势分析等字段
- `test_annual_summary_empty_year`
  - 新用户 → 调用 `/api/annual` → 验证返回空状态或零值，无异常

### 4.7 `test_ws_e2e.py`

WebSocket 测试较为特殊，Playwright 支持 WebSocket 事件监听：

- `test_ws_connection_with_valid_token`
  - 注册用户 → 通过 Playwright 建立 WebSocket 连接 `ws://localhost:8000/api/ws?token=...`
  - 验证连接成功（on open 事件）
- `test_ws_connection_with_invalid_token`
  - 使用伪造 token 连接 → 验证连接被拒绝（close 事件，非 1000）
- `test_ws_message_echo`
  - 建立连接 → 发送 JSON 消息 → 验证收到响应（或服务器行为符合预期）

---

## 5. 目录结构（最终）

```
backend/e2e/
  conftest.py                      # 新增：统一 fixtures + 辅助函数
  test_auth_e2e.py                 # 新增
  test_ai_conversation_e2e.py      # 改造：使用 fixtures
  test_export_e2e.py               # 新增
  test_health_events_e2e.py        # 新增
  test_home_e2e.py                 # 新增
  test_hospital_e2e.py             # 改造：使用 fixtures
  test_indicator_e2e.py            # 改造：使用 fixtures
  test_medications_e2e.py          # 新增
  test_member_e2e.py               # 改造：使用 fixtures
  test_report_e2e.py               # 改造：使用 fixtures
  test_search_e2e.py               # 改造：使用 fixtures
  test_summary_e2e.py              # 新增
  test_timeline_reminder_e2e.py    # 改造：使用 fixtures
  test_vaccine_e2e.py              # 改造：使用 fixtures
  test_ws_e2e.py                   # 新增
  screenshots/                     # Swagger UI 截图目录
```

---

## 6. 运行方式

```bash
# 1. 确保后端服务运行在 localhost:8000
cd backend && uvicorn app.main:app --reload

# 2. 安装 Playwright（首次）
cd backend && pip install -e ".[dev]"
playwright install chromium

# 3. 运行全部 E2E 测试
cd backend && pytest e2e/ -v --tb=short

# 4. 运行单个模块
cd backend && pytest e2e/test_auth_e2e.py -v

# 5. 带截图查看
cd backend && pytest e2e/ -v --headed  # headed 模式便于调试
```

---

## 7. 依赖变更

`backend/pyproject.toml` 已包含 `pytest-asyncio` 和 `minium`，Playwright 需要额外确认：

- `playwright>=1.42.0` 应已作为 `minium` 的依赖存在，或需显式添加
- 若不满足，在 `[project.optional-dependencies] dev` 中追加 `playwright>=1.42.0`

---

## 8. 自我审查

- **Placeholder 扫描**：无 TBD/TODO，所有模块设计完整。
- **内部一致性**：fixture 设计兼容现有测试的 `page.request` / `context.request` 模式；WebSocket 测试使用 Playwright 原生 API，不引入额外依赖。
- **Scope 检查**：本设计聚焦后端 API E2E 测试，不涉及微信小程序前端（继续由 minium 覆盖）和 CI/CD 配置（方案C内容）。
- **Ambiguity 检查**：`registered_user` fixture 每次测试注册独立用户，天然隔离，无需额外清理逻辑。
