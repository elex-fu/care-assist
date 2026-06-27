# Playwright E2E 全面验证实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐后端 FastAPI 全部 15 个 API 模块的 Playwright E2E 测试，统一 fixtures 消除重复代码。

**Architecture:** 新增 `e2e/conftest.py` 提供 `registered_user`、`auth_headers`、`api_context`、`swagger_page` 等 fixtures；现有 8 个测试文件去除内联注册逻辑改为 fixture 注入；新增 7 个缺失模块的测试文件。

**Tech Stack:** Python 3.11, pytest-asyncio, Playwright (Chromium), FastAPI ASGI test transport via `async_playwright` request API.

---

## 文件结构

| 文件 | 动作 | 说明 |
|------|------|------|
| `backend/e2e/conftest.py` | **Create** | 统一 fixtures：浏览器、API context、用户注册、认证 headers、Swagger 截图页 |
| `backend/e2e/test_member_e2e.py` | **Modify** | 使用 fixtures 替代内联注册（验证模板） |
| `backend/e2e/test_vaccine_e2e.py` | **Modify** | 使用 fixtures 替代内联注册 |
| `backend/e2e/test_report_e2e.py` | **Modify** | 使用 fixtures 替代内联注册 |
| `backend/e2e/test_search_e2e.py` | **Modify** | 使用 fixtures 替代内联注册 |
| `backend/e2e/test_ai_conversation_e2e.py` | **Modify** | 使用 fixtures 替代内联注册 |
| `backend/e2e/test_indicator_e2e.py` | **Modify** | 使用 fixtures 替代内联注册 |
| `backend/e2e/test_hospital_e2e.py` | **Modify** | 使用 fixtures 替代内联注册 |
| `backend/e2e/test_timeline_reminder_e2e.py` | **Modify** | 使用 fixtures 替代内联注册 |
| `backend/e2e/test_auth_e2e.py` | **Create** | 认证模块：注册/登录/刷新/非法 token |
| `backend/e2e/test_home_e2e.py` | **Create** | Dashboard：空数据/有数据 |
| `backend/e2e/test_health_events_e2e.py` | **Create** | 健康事件：CRUD + 过滤 + 排序 |
| `backend/e2e/test_medications_e2e.py` | **Create** | 用药管理：CRUD + 服药记录 + 权限隔离 |
| `backend/e2e/test_export_e2e.py` | **Create** | 数据导出：Excel/PDF + 日期范围 |
| `backend/e2e/test_summary_e2e.py` | **Create** | 年度总结：有数据/空数据 |
| `backend/e2e/test_ws_e2e.py` | **Create** | WebSocket：有效/非法 token 连接 |

---

## Task 1: 创建统一 fixtures — `e2e/conftest.py`

**Files:**
- Create: `backend/e2e/conftest.py`

- [ ] **Step 1: 编写 conftest.py**

```python
"""Shared Playwright fixtures for backend E2E tests."""

import json
import os
import uuid

import pytest_asyncio
from playwright.async_api import async_playwright


BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8000")


@pytest_asyncio.fixture(scope="session")
async def playwright_instance():
    async with async_playwright() as p:
        yield p


@pytest_asyncio.fixture(scope="session")
async def browser(playwright_instance):
    browser = await playwright_instance.chromium.launch(headless=True)
    yield browser
    await browser.close()


@pytest_asyncio.fixture(scope="session")
async def api_context(browser):
    context = await browser.new_context()
    yield context
    await context.close()


@pytest_asyncio.fixture(loop_scope="function")
async def registered_user(api_context):
    """Register a new user and return auth info."""
    code = f"mock_e2e_{uuid.uuid4().hex[:8]}"
    creator_name = f"E2E_{uuid.uuid4().hex[:6]}"

    resp = await api_context.request.post(
        f"{BASE_URL}/api/auth/register?creator_name={creator_name}",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"code": code}),
    )
    assert resp.ok, await resp.text()
    body = await resp.json()

    return {
        "token": body["data"]["access_token"],
        "member_id": body["data"]["member"]["id"],
        "family_id": body["data"]["member"]["family_id"],
        "name": creator_name,
    }


@pytest_asyncio.fixture(loop_scope="function")
async def auth_headers(registered_user):
    return {
        "Authorization": f"Bearer {registered_user['token']}",
        "Content-Type": "application/json",
    }


@pytest_asyncio.fixture(loop_scope="function")
async def swagger_page(browser):
    """Provide a fresh browser page for Swagger UI screenshots."""
    page = await browser.new_page(viewport={"width": 1280, "height": 800})
    yield page
    await page.close()
```

- [ ] **Step 2: 验证语法**

Run: `cd backend && python -c "import e2e.conftest"`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add backend/e2e/conftest.py
git commit -m "test(e2e): add unified Playwright fixtures"
```

---

## Task 2: 改造 `test_member_e2e.py`（验证模板）

**Files:**
- Modify: `backend/e2e/test_member_e2e.py`

- [ ] **Step 1: 重写文件**

```python
import json
import uuid

from e2e.conftest import BASE_URL


async def test_swagger_docs_show_members(swagger_page):
    resp = await swagger_page.request.get(f"{BASE_URL}/openapi.json")
    assert resp.ok
    spec = await resp.json()
    paths = spec.get("paths", {})
    assert "/api/members/me" in paths
    assert "/api/members/{member_id}/export" in paths

    await swagger_page.goto(f"{BASE_URL}/docs")
    await swagger_page.wait_for_load_state("networkidle")
    await swagger_page.wait_for_timeout(1000)
    await swagger_page.screenshot(path="e2e/screenshots/swagger_members.png", full_page=False)


async def test_api_member_export_flow_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create an indicator
    resp = await api_context.request.post(
        f"{BASE_URL}/api/indicators",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "indicator_key": "systolic_bp",
            "indicator_name": "收缩压",
            "value": 120.0,
            "unit": "mmHg",
            "record_date": "2024-06-15",
        }),
    )
    assert resp.ok

    # Export member health data
    resp = await api_context.request.get(
        f"{BASE_URL}/api/members/{member_id}/export",
        headers=auth_headers,
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert "member" in data["data"]
    assert len(data["data"]["indicators"]) >= 1
    assert data["data"]["member"]["name"] == registered_user["name"]
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && pytest e2e/test_member_e2e.py -v`
Expected: 2 passed

- [ ] **Step 3: Commit**

```bash
git add backend/e2e/test_member_e2e.py
git commit -m "test(e2e): refactor member e2e to use unified fixtures"
```

---

## Task 3: 改造第一批现有测试（vaccine, report, search）

**Files:**
- Modify: `backend/e2e/test_vaccine_e2e.py`
- Modify: `backend/e2e/test_report_e2e.py`
- Modify: `backend/e2e/test_search_e2e.py`

- [ ] **Step 1: 重写 `test_vaccine_e2e.py`**

```python
import json

from e2e.conftest import BASE_URL


async def test_swagger_docs_show_vaccines(swagger_page):
    resp = await swagger_page.request.get(f"{BASE_URL}/openapi.json")
    assert resp.ok
    spec = await resp.json()
    paths = spec.get("paths", {})
    assert "/api/vaccines" in paths
    assert "post" in paths["/api/vaccines"]
    assert "get" in paths["/api/vaccines"]
    assert "/api/vaccines/{record_id}" in paths
    assert "patch" in paths["/api/vaccines/{record_id}"]
    assert "delete" in paths["/api/vaccines/{record_id}"]

    await swagger_page.goto(f"{BASE_URL}/docs")
    await swagger_page.wait_for_load_state("networkidle")
    await swagger_page.wait_for_timeout(1000)
    await swagger_page.screenshot(path="e2e/screenshots/swagger_vaccines.png", full_page=False)


async def test_api_vaccine_flow_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create pending vaccine record
    resp = await api_context.request.post(
        f"{BASE_URL}/api/vaccines",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "vaccine_name": "乙肝疫苗",
            "dose": 1,
            "scheduled_date": "2024-06-01",
            "status": "pending",
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    record_id = data["data"]["id"]
    assert data["data"]["vaccine_name"] == "乙肝疫苗"
    assert data["data"]["status"] == "pending"

    # List vaccines
    resp = await api_context.request.get(
        f"{BASE_URL}/api/vaccines?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert len(data["data"]) >= 1

    # Filter by pending
    resp = await api_context.request.get(
        f"{BASE_URL}/api/vaccines?member_id={member_id}&status=pending",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert all(r["status"] == "pending" for r in data["data"])

    # Mark as completed
    resp = await api_context.request.patch(
        f"{BASE_URL}/api/vaccines/{record_id}",
        headers=auth_headers,
        data=json.dumps({
            "status": "completed",
            "actual_date": "2024-06-01",
            "location": "社区医院",
            "batch_no": "B20240601",
            "reaction": "无不良反应",
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert data["data"]["status"] == "completed"
    assert data["data"]["location"] == "社区医院"

    # Delete record
    resp = await api_context.request.delete(
        f"{BASE_URL}/api/vaccines/{record_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"]["deleted"] is True
```

- [ ] **Step 2: 重写 `test_report_e2e.py`**

```python
import json

from e2e.conftest import BASE_URL


async def test_swagger_docs_show_reports(swagger_page):
    resp = await swagger_page.request.get(f"{BASE_URL}/openapi.json")
    assert resp.ok
    spec = await resp.json()
    paths = spec.get("paths", {})
    assert "/api/reports" in paths
    assert "post" in paths["/api/reports"]
    assert "get" in paths["/api/reports"]
    assert "/api/reports/{report_id}" in paths
    assert "delete" in paths["/api/reports/{report_id}"]
    assert "/api/reports/{report_id}/ocr" in paths
    assert "post" in paths["/api/reports/{report_id}/ocr"]

    await swagger_page.goto(f"{BASE_URL}/docs")
    await swagger_page.wait_for_load_state("networkidle")
    await swagger_page.wait_for_timeout(1000)
    await swagger_page.screenshot(path="e2e/screenshots/swagger_reports.png", full_page=False)


async def test_api_report_flow_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create report with a fake image
    resp = await api_context.request.post(
        f"{BASE_URL}/api/reports",
        headers={"Authorization": auth_headers["Authorization"]},
        multipart={
            "member_id": member_id,
            "type": "lab",
            "hospital": "测试医院",
            "department": "内科",
            "report_date": "2024-06-15",
            "images": {
                "name": "bp_report.jpg",
                "mimeType": "image/jpeg",
                "buffer": b"fake image bytes for ocr",
            },
        },
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    report_id = data["data"]["id"]
    assert data["data"]["type"] == "lab"
    assert data["data"]["ocr_status"] == "pending"

    # List reports
    resp = await api_context.request.get(
        f"{BASE_URL}/api/reports?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert len(data["data"]["reports"]) >= 1

    # Trigger OCR
    resp = await api_context.request.post(
        f"{BASE_URL}/api/reports/{report_id}/ocr",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"]["ocr_status"] == "completed"
    assert len(data["data"]["extracted"]) > 0

    # Delete report
    resp = await api_context.request.delete(
        f"{BASE_URL}/api/reports/{report_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"]["deleted"] is True
```

- [ ] **Step 3: 重写 `test_search_e2e.py`**

```python
import json

from e2e.conftest import BASE_URL


async def test_swagger_docs_show_search(swagger_page):
    resp = await swagger_page.request.get(f"{BASE_URL}/openapi.json")
    assert resp.ok
    spec = await resp.json()
    paths = spec.get("paths", {})
    assert "/api/search" in paths
    assert "get" in paths["/api/search"]

    await swagger_page.goto(f"{BASE_URL}/docs")
    await swagger_page.wait_for_load_state("networkidle")
    await swagger_page.wait_for_timeout(1000)
    await swagger_page.screenshot(path="e2e/screenshots/swagger_search.png", full_page=False)


async def test_api_search_flow_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create an indicator
    resp = await api_context.request.post(
        f"{BASE_URL}/api/indicators",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "indicator_key": "systolic_bp",
            "indicator_name": "收缩压",
            "value": 125.0,
            "unit": "mmHg",
            "record_date": "2024-06-15",
        }),
    )
    assert resp.ok

    # Create a reminder
    resp = await api_context.request.post(
        f"{BASE_URL}/api/reminders",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "type": "checkup",
            "title": "体检提醒",
            "scheduled_date": "2024-08-01",
            "status": "pending",
        }),
    )
    assert resp.ok

    # Search across all types
    resp = await api_context.request.get(
        f"{BASE_URL}/api/search?q=收缩压",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert any(r["entity_type"] == "indicator" for r in data["data"])

    # Search reminders
    resp = await api_context.request.get(
        f"{BASE_URL}/api/search?q=体检",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert any(r["entity_type"] == "reminder" for r in data["data"])

    # Filter by entity type
    resp = await api_context.request.get(
        f"{BASE_URL}/api/search?q=收缩压&entity_types=indicator",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert all(r["entity_type"] == "indicator" for r in data["data"])

    # Search with member filter
    resp = await api_context.request.get(
        f"{BASE_URL}/api/search?q=体检&member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert all(r["member_id"] == member_id for r in data["data"])

    # No results search
    resp = await api_context.request.get(
        f"{BASE_URL}/api/search?q=xyz123不存在",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"] == []
```

- [ ] **Step 4: 运行测试**

Run: `cd backend && pytest e2e/test_vaccine_e2e.py e2e/test_report_e2e.py e2e/test_search_e2e.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add backend/e2e/test_vaccine_e2e.py backend/e2e/test_report_e2e.py backend/e2e/test_search_e2e.py
git commit -m "test(e2e): refactor vaccine/report/search e2e to use unified fixtures"
```

---

## Task 4: 改造第二批现有测试（ai_conversation, indicator）

**Files:**
- Modify: `backend/e2e/test_ai_conversation_e2e.py`
- Modify: `backend/e2e/test_indicator_e2e.py`

- [ ] **Step 1: 重写 `test_ai_conversation_e2e.py`**

```python
import json

from e2e.conftest import BASE_URL


async def test_swagger_docs_show_ai_conversations(swagger_page):
    resp = await swagger_page.request.get(f"{BASE_URL}/openapi.json")
    assert resp.ok
    spec = await resp.json()
    paths = spec.get("paths", {})
    assert "/api/ai-conversations" in paths
    assert "post" in paths["/api/ai-conversations"]
    assert "get" in paths["/api/ai-conversations"]
    assert "/api/ai-conversations/{conversation_id}/messages" in paths
    assert "post" in paths["/api/ai-conversations/{conversation_id}/messages"]
    assert "/api/ai-conversations/{conversation_id}" in paths
    assert "delete" in paths["/api/ai-conversations/{conversation_id}"]

    await swagger_page.goto(f"{BASE_URL}/docs")
    await swagger_page.wait_for_load_state("networkidle")
    await swagger_page.wait_for_timeout(1000)
    await swagger_page.screenshot(path="e2e/screenshots/swagger_ai_conversations.png", full_page=False)


async def test_api_ai_conversation_flow_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create conversation
    resp = await api_context.request.post(
        f"{BASE_URL}/api/ai-conversations",
        headers=auth_headers,
        data=json.dumps({"member_id": member_id, "page_context": "home"}),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    conv_id = data["data"]["id"]
    assert data["data"]["member_id"] == member_id
    assert data["data"]["messages"] == []

    # Send greeting message
    resp = await api_context.request.post(
        f"{BASE_URL}/api/ai-conversations/{conv_id}/messages",
        headers=auth_headers,
        data=json.dumps({"user_message": "你好"}),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert "reply" in data["data"]
    assert len(data["data"]["messages"]) == 2

    # Send indicator question (no data yet)
    resp = await api_context.request.post(
        f"{BASE_URL}/api/ai-conversations/{conv_id}/messages",
        headers=auth_headers,
        data=json.dumps({"user_message": "血压怎么样"}),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert "还没有记录" in data["data"]["reply"] or "建议定期记录" in data["data"]["reply"]

    # List conversations
    resp = await api_context.request.get(
        f"{BASE_URL}/api/ai-conversations?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert len(data["data"]) >= 1
    assert data["data"][0]["message_count"] == 4

    # Delete conversation
    resp = await api_context.request.delete(
        f"{BASE_URL}/api/ai-conversations/{conv_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"]["deleted"] is True
```

- [ ] **Step 2: 重写 `test_indicator_e2e.py`**

```python
import json

from e2e.conftest import BASE_URL


async def test_swagger_docs_show_indicators(swagger_page):
    resp = await swagger_page.request.get(f"{BASE_URL}/openapi.json")
    assert resp.ok
    spec = await resp.json()
    paths = spec.get("paths", {})
    assert "/api/indicators" in paths
    assert "post" in paths["/api/indicators"]
    assert "get" in paths["/api/indicators"]
    indicator_id_path = "/api/indicators/{indicator_id}"
    assert indicator_id_path in paths
    assert "delete" in paths[indicator_id_path]

    await swagger_page.goto(f"{BASE_URL}/docs")
    await swagger_page.wait_for_load_state("networkidle")
    await swagger_page.wait_for_timeout(1000)
    await swagger_page.screenshot(path="e2e/screenshots/swagger_indicators.png", full_page=False)


async def test_api_indicator_flow_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create indicator
    resp = await api_context.request.post(
        f"{BASE_URL}/api/indicators",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "indicator_key": "systolic_bp",
            "indicator_name": "收缩压",
            "value": 135.0,
            "unit": "mmHg",
            "record_date": "2024-06-15",
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert data["data"]["status"] == "normal"
    assert data["data"]["indicator_key"] == "systolic_bp"
    indicator_id = data["data"]["id"]

    # List indicators
    resp = await api_context.request.get(
        f"{BASE_URL}/api/indicators?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert len(data["data"]) >= 1

    # Get trend
    resp = await api_context.request.get(
        f"{BASE_URL}/api/indicators/trend?member_id={member_id}&indicator_key=systolic_bp",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert "trend" in data["data"]

    # Delete indicator
    resp = await api_context.request.delete(
        f"{BASE_URL}/api/indicators/{indicator_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"]["deleted"] is True


async def test_api_batch_indicator_flow_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    resp = await api_context.request.post(
        f"{BASE_URL}/api/indicators/batch",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "items": [
                {
                    "indicator_key": "systolic_bp",
                    "indicator_name": "收缩压",
                    "value": 120.0,
                    "unit": "mmHg",
                    "record_date": "2024-06-15",
                },
                {
                    "indicator_key": "diastolic_bp",
                    "indicator_name": "舒张压",
                    "value": 80.0,
                    "unit": "mmHg",
                    "record_date": "2024-06-15",
                },
            ],
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert len(data["data"]) == 2
    assert data["data"][0]["indicator_key"] == "systolic_bp"
    assert data["data"][1]["indicator_key"] == "diastolic_bp"
```

- [ ] **Step 3: 运行测试**

Run: `cd backend && pytest e2e/test_ai_conversation_e2e.py e2e/test_indicator_e2e.py -v`
Expected: 5 passed

- [ ] **Step 4: Commit**

```bash
git add backend/e2e/test_ai_conversation_e2e.py backend/e2e/test_indicator_e2e.py
git commit -m "test(e2e): refactor ai-conversation/indicator e2e to use unified fixtures"
```

---

## Task 5: 改造第三批现有测试（hospital, timeline_reminder）

**Files:**
- Modify: `backend/e2e/test_hospital_e2e.py`
- Modify: `backend/e2e/test_timeline_reminder_e2e.py`

- [ ] **Step 1: 重写 `test_hospital_e2e.py`**

```python
import json
from datetime import datetime, timedelta

from e2e.conftest import BASE_URL


async def test_swagger_docs_show_hospital_events(swagger_page):
    resp = await swagger_page.request.get(f"{BASE_URL}/openapi.json")
    assert resp.ok
    spec = await resp.json()
    paths = spec.get("paths", {})
    assert "/api/hospital-events" in paths
    assert "post" in paths["/api/hospital-events"]
    assert "get" in paths["/api/hospital-events"]
    assert "/api/hospital-events/{event_id}" in paths
    assert "patch" in paths["/api/hospital-events/{event_id}"]
    assert "delete" in paths["/api/hospital-events/{event_id}"]

    await swagger_page.goto(f"{BASE_URL}/docs")
    await swagger_page.wait_for_load_state("networkidle")
    await swagger_page.wait_for_timeout(1000)
    await swagger_page.screenshot(path="e2e/screenshots/swagger_hospitals.png", full_page=False)


async def test_api_hospital_event_flow_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create active hospital event
    resp = await api_context.request.post(
        f"{BASE_URL}/api/hospital-events",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "hospital": "协和医院",
            "department": "心内科",
            "admission_date": "2024-06-01",
            "diagnosis": "高血压观察",
            "doctor": "李医生",
            "key_nodes": [
                {"date": "2024-06-01", "event": "入院", "notes": "血压180/110"},
            ],
            "watch_indicators": ["systolic_bp", "diastolic_bp"],
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    event_id = data["data"]["id"]
    assert data["data"]["hospital"] == "协和医院"
    assert data["data"]["status"] == "active"

    # List events
    resp = await api_context.request.get(
        f"{BASE_URL}/api/hospital-events?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert len(data["data"]) >= 1

    # Filter by active status
    resp = await api_context.request.get(
        f"{BASE_URL}/api/hospital-events?member_id={member_id}&status=active",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert all(e["status"] == "active" for e in data["data"])

    # Update with discharge date
    resp = await api_context.request.patch(
        f"{BASE_URL}/api/hospital-events/{event_id}",
        headers=auth_headers,
        data=json.dumps({
            "discharge_date": "2024-06-10",
            "diagnosis": "高血压，已稳定",
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert data["data"]["status"] == "discharged"
    assert data["data"]["discharge_date"] == "2024-06-10"

    # Delete event
    resp = await api_context.request.delete(
        f"{BASE_URL}/api/hospital-events/{event_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"]["deleted"] is True


async def test_api_hospital_watch_and_compare_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    # Create hospital event with watch indicators
    resp = await api_context.request.post(
        f"{BASE_URL}/api/hospital-events",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "hospital": "同仁医院",
            "department": "心内科",
            "admission_date": "2024-06-01",
            "diagnosis": "高血压观察",
            "watch_indicators": ["systolic_bp", "diastolic_bp"],
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    event_id = data["data"]["id"]

    # Yesterday indicator
    resp = await api_context.request.post(
        f"{BASE_URL}/api/indicators",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "indicator_key": "systolic_bp",
            "indicator_name": "收缩压",
            "value": 120.0,
            "unit": "mmHg",
            "record_date": yesterday.isoformat(),
            "source_hospital_id": event_id,
        }),
    )
    assert resp.ok

    # Today indicator
    resp = await api_context.request.post(
        f"{BASE_URL}/api/indicators",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "indicator_key": "systolic_bp",
            "indicator_name": "收缩压",
            "value": 130.0,
            "unit": "mmHg",
            "record_date": today.isoformat(),
            "source_hospital_id": event_id,
        }),
    )
    assert resp.ok

    # Get watch indicators
    resp = await api_context.request.get(
        f"{BASE_URL}/api/hospital-events/{event_id}/watch",
        headers=auth_headers,
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert len(data["data"]) >= 1
    watch_item = data["data"][0]
    assert watch_item["indicator_key"] == "systolic_bp"
    assert watch_item["value"] == 130.0
    assert watch_item["previous_value"] == 120.0

    # Get comparison
    resp = await api_context.request.get(
        f"{BASE_URL}/api/hospital-events/{event_id}/compare",
        headers=auth_headers,
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert data["data"]["event_id"] == event_id
    assert data["data"]["total"] >= 1
```

- [ ] **Step 2: 重写 `test_timeline_reminder_e2e.py`**

```python
import json

from e2e.conftest import BASE_URL


async def test_swagger_docs_show_timeline_and_reminders(swagger_page):
    resp = await swagger_page.request.get(f"{BASE_URL}/openapi.json")
    assert resp.ok
    spec = await resp.json()
    paths = spec.get("paths", {})
    assert "/api/health-events" in paths
    assert "/api/reminders" in paths

    await swagger_page.goto(f"{BASE_URL}/docs")
    await swagger_page.wait_for_load_state("networkidle")
    await swagger_page.wait_for_timeout(1000)
    await swagger_page.screenshot(path="e2e/screenshots/swagger_timeline_reminders.png", full_page=False)


async def test_api_reminder_flow_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create reminder
    resp = await api_context.request.post(
        f"{BASE_URL}/api/reminders",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "type": "checkup",
            "title": "年度体检",
            "description": "记得空腹，带身份证",
            "scheduled_date": "2024-08-01",
            "status": "pending",
            "priority": "high",
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    reminder_id = data["data"]["id"]
    assert data["data"]["type"] == "checkup"
    assert data["data"]["priority"] == "high"

    # List reminders
    resp = await api_context.request.get(
        f"{BASE_URL}/api/reminders?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert len(data["data"]) >= 1

    # Filter pending
    resp = await api_context.request.get(
        f"{BASE_URL}/api/reminders?member_id={member_id}&status=pending",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert all(r["status"] == "pending" for r in data["data"])

    # Complete reminder
    resp = await api_context.request.patch(
        f"{BASE_URL}/api/reminders/{reminder_id}",
        headers=auth_headers,
        data=json.dumps({
            "status": "completed",
            "completed_date": "2024-08-01",
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert data["data"]["status"] == "completed"

    # Delete reminder
    resp = await api_context.request.delete(
        f"{BASE_URL}/api/reminders/{reminder_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"]["deleted"] is True


async def test_api_health_timeline_flow_via_playwright(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create visit event
    resp = await api_context.request.post(
        f"{BASE_URL}/api/health-events",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "type": "visit",
            "event_date": "2024-06-15",
            "hospital": "协和医院",
            "department": "心内科",
            "doctor": "李医生",
            "diagnosis": "高血压",
            "notes": "开了降压药",
            "status": "abnormal",
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    event_id = data["data"]["id"]
    assert data["data"]["type"] == "visit"
    assert data["data"]["status"] == "abnormal"

    # Create milestone event
    resp = await api_context.request.post(
        f"{BASE_URL}/api/health-events",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "type": "milestone",
            "event_date": "2024-06-01",
            "notes": "第一次独立行走",
            "status": "normal",
        }),
    )
    assert resp.ok

    # List all events
    resp = await api_context.request.get(
        f"{BASE_URL}/api/health-events?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert len(data["data"]) >= 2

    # Filter by type
    resp = await api_context.request.get(
        f"{BASE_URL}/api/health-events?member_id={member_id}&type=milestone",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert all(e["type"] == "milestone" for e in data["data"])

    # Update event
    resp = await api_context.request.patch(
        f"{BASE_URL}/api/health-events/{event_id}",
        headers=auth_headers,
        data=json.dumps({
            "notes": "开了降压药，每日一片",
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert data["data"]["notes"] == "开了降压药，每日一片"

    # Delete event
    resp = await api_context.request.delete(
        f"{BASE_URL}/api/health-events/{event_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"]["deleted"] is True
```

- [ ] **Step 3: 运行测试**

Run: `cd backend && pytest e2e/test_hospital_e2e.py e2e/test_timeline_reminder_e2e.py -v`
Expected: 6 passed

- [ ] **Step 4: Commit**

```bash
git add backend/e2e/test_hospital_e2e.py backend/e2e/test_timeline_reminder_e2e.py
git commit -m "test(e2e): refactor hospital/timeline-reminder e2e to use unified fixtures"
```

---

## Task 6: 创建 `test_auth_e2e.py`

**Files:**
- Create: `backend/e2e/test_auth_e2e.py`

- [ ] **Step 1: 编写测试文件**

```python
import json
import uuid

import pytest

from e2e.conftest import BASE_URL


async def test_swagger_docs_show_auth(swagger_page):
    resp = await swagger_page.request.get(f"{BASE_URL}/openapi.json")
    assert resp.ok
    spec = await resp.json()
    paths = spec.get("paths", {})
    assert "/api/login" in paths
    assert "/api/register" in paths
    assert "/api/refresh" in paths

    await swagger_page.goto(f"{BASE_URL}/docs")
    await swagger_page.wait_for_load_state("networkidle")
    await swagger_page.wait_for_timeout(1000)
    await swagger_page.screenshot(path="e2e/screenshots/swagger_auth.png", full_page=False)


async def test_register_and_login_flow(api_context):
    code = f"mock_e2e_{uuid.uuid4().hex[:8]}"
    creator_name = f"E2EAuth_{uuid.uuid4().hex[:6]}"

    # Register
    resp = await api_context.request.post(
        f"{BASE_URL}/api/auth/register?creator_name={creator_name}",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"code": code}),
    )
    assert resp.ok, await resp.text()
    register_body = await resp.json()
    access_token = register_body["data"]["access_token"]
    assert access_token
    assert register_body["data"]["member"]["name"] == creator_name

    # Login with same code
    resp = await api_context.request.post(
        f"{BASE_URL}/api/auth/login",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"code": code}),
    )
    assert resp.ok, await resp.text()
    login_body = await resp.json()
    assert login_body["data"]["access_token"]
    assert login_body["data"]["member"]["name"] == creator_name


async def test_refresh_token_flow(api_context):
    code = f"mock_e2e_{uuid.uuid4().hex[:8]}"
    creator_name = f"E2ERefresh_{uuid.uuid4().hex[:6]}"

    # Register
    resp = await api_context.request.post(
        f"{BASE_URL}/api/auth/register?creator_name={creator_name}",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"code": code}),
    )
    assert resp.ok, await resp.text()
    body = await resp.json()
    refresh_token = body["data"]["refresh_token"]

    # Refresh
    resp = await api_context.request.post(
        f"{BASE_URL}/api/auth/refresh",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"refresh_token": refresh_token}),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert "access_token" in data["data"]
    assert data["data"]["access_token"]


async def test_me_endpoint_with_invalid_token(api_context):
    headers = {"Authorization": "Bearer invalid_token_12345"}
    resp = await api_context.request.get(
        f"{BASE_URL}/api/members/me",
        headers=headers,
    )
    assert resp.status == 401
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && pytest e2e/test_auth_e2e.py -v`
Expected: 4 passed

- [ ] **Step 3: Commit**

```bash
git add backend/e2e/test_auth_e2e.py
git commit -m "test(e2e): add auth e2e tests"
```

---

## Task 7: 创建 `test_home_e2e.py`

**Files:**
- Create: `backend/e2e/test_home_e2e.py`

- [ ] **Step 1: 编写测试文件**

```python
import json

from e2e.conftest import BASE_URL


async def test_swagger_docs_show_dashboard(swagger_page):
    resp = await swagger_page.request.get(f"{BASE_URL}/openapi.json")
    assert resp.ok
    spec = await resp.json()
    paths = spec.get("paths", {})
    assert "/api/dashboard" in paths

    await swagger_page.goto(f"{BASE_URL}/docs")
    await swagger_page.wait_for_load_state("networkidle")
    await swagger_page.wait_for_timeout(1000)
    await swagger_page.screenshot(path="e2e/screenshots/swagger_home.png", full_page=False)


async def test_dashboard_with_empty_data(api_context, registered_user, auth_headers):
    resp = await api_context.request.get(
        f"{BASE_URL}/api/dashboard",
        headers=auth_headers,
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert "data" in data
    # Should return valid structure even with no data
    dashboard = data["data"]
    assert "members" in dashboard or "family" in dashboard or "recent" in dashboard


async def test_dashboard_with_data(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Add another member
    resp = await api_context.request.post(
        f"{BASE_URL}/api/members",
        headers=auth_headers,
        data=json.dumps({
            "name": "孩子",
            "gender": "male",
            "type": "child",
        }),
    )
    assert resp.ok

    # Create indicator
    resp = await api_context.request.post(
        f"{BASE_URL}/api/indicators",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "indicator_key": "systolic_bp",
            "indicator_name": "收缩压",
            "value": 120.0,
            "unit": "mmHg",
            "record_date": "2024-06-15",
        }),
    )
    assert resp.ok

    # Create reminder
    resp = await api_context.request.post(
        f"{BASE_URL}/api/reminders",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "type": "checkup",
            "title": "体检",
            "scheduled_date": "2024-08-01",
            "status": "pending",
        }),
    )
    assert resp.ok

    # Get dashboard
    resp = await api_context.request.get(
        f"{BASE_URL}/api/dashboard",
        headers=auth_headers,
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    dashboard = data["data"]
    assert dashboard is not None
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && pytest e2e/test_home_e2e.py -v`
Expected: 3 passed

- [ ] **Step 3: Commit**

```bash
git add backend/e2e/test_home_e2e.py
git commit -m "test(e2e): add home dashboard e2e tests"
```

---

## Task 8: 创建 `test_health_events_e2e.py`

**Files:**
- Create: `backend/e2e/test_health_events_e2e.py`

- [ ] **Step 1: 编写测试文件**

```python
import json

from e2e.conftest import BASE_URL


async def test_swagger_docs_show_health_events(swagger_page):
    resp = await swagger_page.request.get(f"{BASE_URL}/openapi.json")
    assert resp.ok
    spec = await resp.json()
    paths = spec.get("paths", {})
    assert "/api/health-events" in paths
    assert "post" in paths["/api/health-events"]
    assert "get" in paths["/api/health-events"]
    assert "/api/health-events/{event_id}" in paths
    assert "patch" in paths["/api/health-events/{event_id}"]
    assert "delete" in paths["/api/health-events/{event_id}"]

    await swagger_page.goto(f"{BASE_URL}/docs")
    await swagger_page.wait_for_load_state("networkidle")
    await swagger_page.wait_for_timeout(1000)
    await swagger_page.screenshot(path="e2e/screenshots/swagger_health_events.png", full_page=False)


async def test_health_event_crud_flow(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create event
    resp = await api_context.request.post(
        f"{BASE_URL}/api/health-events",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "type": "visit",
            "event_date": "2024-06-15",
            "hospital": "协和医院",
            "department": "心内科",
            "doctor": "李医生",
            "diagnosis": "高血压",
            "notes": "开了降压药",
            "status": "abnormal",
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    event_id = data["data"]["id"]
    assert data["data"]["type"] == "visit"

    # List
    resp = await api_context.request.get(
        f"{BASE_URL}/api/health-events?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert len(data["data"]) >= 1

    # Update
    resp = await api_context.request.patch(
        f"{BASE_URL}/api/health-events/{event_id}",
        headers=auth_headers,
        data=json.dumps({"notes": "更新备注"}),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert data["data"]["notes"] == "更新备注"

    # Delete
    resp = await api_context.request.delete(
        f"{BASE_URL}/api/health-events/{event_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"]["deleted"] is True


async def test_health_event_filter_by_type(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create multiple types
    for evt_type in ["visit", "milestone"]:
        resp = await api_context.request.post(
            f"{BASE_URL}/api/health-events",
            headers=auth_headers,
            data=json.dumps({
                "member_id": member_id,
                "type": evt_type,
                "event_date": "2024-06-15",
                "notes": f"{evt_type} event",
                "status": "normal",
            }),
        )
        assert resp.ok

    # Filter by visit
    resp = await api_context.request.get(
        f"{BASE_URL}/api/health-events?member_id={member_id}&type=visit",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert all(e["type"] == "visit" for e in data["data"])

    # Filter by milestone
    resp = await api_context.request.get(
        f"{BASE_URL}/api/health-events?member_id={member_id}&type=milestone",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert all(e["type"] == "milestone" for e in data["data"])


async def test_health_event_timeline_order(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create events on different dates
    for day in ["2024-06-01", "2024-06-15", "2024-06-10"]:
        resp = await api_context.request.post(
            f"{BASE_URL}/api/health-events",
            headers=auth_headers,
            data=json.dumps({
                "member_id": member_id,
                "type": "visit",
                "event_date": day,
                "notes": f"event on {day}",
                "status": "normal",
            }),
        )
        assert resp.ok

    # List and verify order (newest first)
    resp = await api_context.request.get(
        f"{BASE_URL}/api/health-events?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    dates = [e["event_date"] for e in data["data"]]
    assert dates == sorted(dates, reverse=True)
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && pytest e2e/test_health_events_e2e.py -v`
Expected: 5 passed

- [ ] **Step 3: Commit**

```bash
git add backend/e2e/test_health_events_e2e.py
git commit -m "test(e2e): add health-events e2e tests"
```

---

## Task 9: 创建 `test_medications_e2e.py`

**Files:**
- Create: `backend/e2e/test_medications_e2e.py`

- [ ] **Step 1: 编写测试文件**

```python
import json

from e2e.conftest import BASE_URL


async def test_swagger_docs_show_medications(swagger_page):
    resp = await swagger_page.request.get(f"{BASE_URL}/openapi.json")
    assert resp.ok
    spec = await resp.json()
    paths = spec.get("paths", {})
    assert "/api/medications" in paths
    assert "post" in paths["/api/medications"]
    assert "get" in paths["/api/medications"]
    assert "/api/medications/{medication_id}" in paths
    assert "patch" in paths["/api/medications/{medication_id}"]
    assert "delete" in paths["/api/medications/{medication_id}"]
    assert "/api/medications/{medication_id}/take" in paths

    await swagger_page.goto(f"{BASE_URL}/docs")
    await swagger_page.wait_for_load_state("networkidle")
    await swagger_page.wait_for_timeout(1000)
    await swagger_page.screenshot(path="e2e/screenshots/swagger_medications.png", full_page=False)


async def test_medication_crud_flow(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create
    resp = await api_context.request.post(
        f"{BASE_URL}/api/medications",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "name": "阿司匹林",
            "dosage": "100mg",
            "frequency": "每日一次",
            "start_date": "2024-06-01",
            "end_date": "2024-06-30",
            "notes": "饭后服用",
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    med_id = data["data"]["id"]
    assert data["data"]["name"] == "阿司匹林"

    # List
    resp = await api_context.request.get(
        f"{BASE_URL}/api/medications?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert len(data["data"]) >= 1

    # Get detail
    resp = await api_context.request.get(
        f"{BASE_URL}/api/medications/{med_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"]["name"] == "阿司匹林"

    # Update
    resp = await api_context.request.patch(
        f"{BASE_URL}/api/medications/{med_id}",
        headers=auth_headers,
        data=json.dumps({"dosage": "50mg"}),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert data["data"]["dosage"] == "50mg"

    # Delete
    resp = await api_context.request.delete(
        f"{BASE_URL}/api/medications/{med_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert data["data"]["deleted"] is True


async def test_medication_take_flow(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create medication
    resp = await api_context.request.post(
        f"{BASE_URL}/api/medications",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "name": "维生素C",
            "dosage": "500mg",
            "frequency": "每日一次",
            "start_date": "2024-06-01",
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    med_id = data["data"]["id"]

    # Take medication
    resp = await api_context.request.post(
        f"{BASE_URL}/api/medications/{med_id}/take",
        headers=auth_headers,
        data=json.dumps({"taken_at": "2024-06-15T08:00:00", "notes": "早餐後"}),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert data["data"]["medication_id"] == med_id

    # Verify log in detail
    resp = await api_context.request.get(
        f"{BASE_URL}/api/medications/{med_id}",
        headers=auth_headers,
    )
    assert resp.ok
    data = await resp.json()
    assert len(data["data"]["logs"]) >= 1
    assert data["data"]["logs"][0]["notes"] == "早餐後"


async def test_medication_permission_isolation(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create medication for user A
    resp = await api_context.request.post(
        f"{BASE_URL}/api/medications",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "name": "私有药物",
            "dosage": "10mg",
            "frequency": "每日一次",
            "start_date": "2024-06-01",
        }),
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    med_id = data["data"]["id"]

    # Register user B in a different family
    import uuid
    code_b = f"mock_e2e_{uuid.uuid4().hex[:8]}"
    resp = await api_context.request.post(
        f"{BASE_URL}/api/auth/register?creator_name=E2EOther",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"code": code_b}),
    )
    assert resp.ok, await resp.text()
    body = await resp.json()
    token_b = body["data"]["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}", "Content-Type": "application/json"}

    # User B tries to access user A's medication
    resp = await api_context.request.get(
        f"{BASE_URL}/api/medications/{med_id}",
        headers=headers_b,
    )
    assert resp.status == 403
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && pytest e2e/test_medications_e2e.py -v`
Expected: 5 passed

- [ ] **Step 3: Commit**

```bash
git add backend/e2e/test_medications_e2e.py
git commit -m "test(e2e): add medications e2e tests"
```

---

## Task 10: 创建 `test_export_e2e.py`

**Files:**
- Create: `backend/e2e/test_export_e2e.py`

- [ ] **Step 1: 编写测试文件**

```python
import json

from e2e.conftest import BASE_URL


async def test_swagger_docs_show_export(swagger_page):
    resp = await swagger_page.request.get(f"{BASE_URL}/openapi.json")
    assert resp.ok
    spec = await resp.json()
    paths = spec.get("paths", {})
    assert "/api/export/excel" in paths
    assert "/api/export/pdf" in paths

    await swagger_page.goto(f"{BASE_URL}/docs")
    await swagger_page.wait_for_load_state("networkidle")
    await swagger_page.wait_for_timeout(1000)
    await swagger_page.screenshot(path="e2e/screenshots/swagger_export.png", full_page=False)


async def test_export_excel_flow(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create indicator
    resp = await api_context.request.post(
        f"{BASE_URL}/api/indicators",
        headers=auth_headers,
        data=json.dumps({
            "member_id": member_id,
            "indicator_key": "systolic_bp",
            "indicator_name": "收缩压",
            "value": 120.0,
            "unit": "mmHg",
            "record_date": "2024-06-15",
        }),
    )
    assert resp.ok

    # Export Excel
    resp = await api_context.request.get(
        f"{BASE_URL}/api/export/excel?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    content_disp = resp.headers.get("content-disposition", "")
    assert ".xlsx" in content_disp
    content_type = resp.headers.get("content-type", "")
    assert "spreadsheetml" in content_type or "octet-stream" in content_type
    body = await resp.body()
    assert len(body) > 0


async def test_export_pdf_flow(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Export PDF
    resp = await api_context.request.get(
        f"{BASE_URL}/api/export/pdf?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok
    content_disp = resp.headers.get("content-disposition", "")
    assert ".pdf" in content_disp
    content_type = resp.headers.get("content-type", "")
    assert "pdf" in content_type or "octet-stream" in content_type
    body = await resp.body()
    assert len(body) > 0


async def test_export_with_date_range(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create indicators on different dates
    for date_str in ["2024-01-15", "2024-06-15", "2024-12-15"]:
        resp = await api_context.request.post(
            f"{BASE_URL}/api/indicators",
            headers=auth_headers,
            data=json.dumps({
                "member_id": member_id,
                "indicator_key": "systolic_bp",
                "indicator_name": "收缩压",
                "value": 120.0,
                "unit": "mmHg",
                "record_date": date_str,
            }),
        )
        assert resp.ok

    # Export with date range
    resp = await api_context.request.get(
        f"{BASE_URL}/api/export/excel?member_id={member_id}&start_date=2024-06-01&end_date=2024-06-30",
        headers=auth_headers,
    )
    assert resp.ok
    body = await resp.body()
    assert len(body) > 0
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && pytest e2e/test_export_e2e.py -v`
Expected: 4 passed

- [ ] **Step 3: Commit**

```bash
git add backend/e2e/test_export_e2e.py
git commit -m "test(e2e): add export e2e tests"
```

---

## Task 11: 创建 `test_summary_e2e.py`

**Files:**
- Create: `backend/e2e/test_summary_e2e.py`

- [ ] **Step 1: 编写测试文件**

```python
import json

from e2e.conftest import BASE_URL


async def test_swagger_docs_show_summary(swagger_page):
    resp = await swagger_page.request.get(f"{BASE_URL}/openapi.json")
    assert resp.ok
    spec = await resp.json()
    paths = spec.get("paths", {})
    assert "/api/annual" in paths

    await swagger_page.goto(f"{BASE_URL}/docs")
    await swagger_page.wait_for_load_state("networkidle")
    await swagger_page.wait_for_timeout(1000)
    await swagger_page.screenshot(path="e2e/screenshots/swagger_summary.png", full_page=False)


async def test_annual_summary_with_data(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    # Create indicators across months
    for month in ["2024-01-15", "2024-06-15", "2024-11-15"]:
        resp = await api_context.request.post(
            f"{BASE_URL}/api/indicators",
            headers=auth_headers,
            data=json.dumps({
                "member_id": member_id,
                "indicator_key": "systolic_bp",
                "indicator_name": "收缩压",
                "value": 120.0,
                "unit": "mmHg",
                "record_date": month,
            }),
        )
        assert resp.ok

    # Get annual summary
    resp = await api_context.request.get(
        f"{BASE_URL}/api/annual?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert "data" in data
    summary = data["data"]
    assert summary is not None


async def test_annual_summary_empty_year(api_context, registered_user, auth_headers):
    member_id = registered_user["member_id"]

    resp = await api_context.request.get(
        f"{BASE_URL}/api/annual?member_id={member_id}",
        headers=auth_headers,
    )
    assert resp.ok, await resp.text()
    data = await resp.json()
    assert "data" in data
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && pytest e2e/test_summary_e2e.py -v`
Expected: 3 passed

- [ ] **Step 3: Commit**

```bash
git add backend/e2e/test_summary_e2e.py
git commit -m "test(e2e): add summary e2e tests"
```

---

## Task 12: 创建 `test_ws_e2e.py`

**Files:**
- Create: `backend/e2e/test_ws_e2e.py`

- [ ] **Step 1: 编写测试文件**

```python
import json
import uuid

from e2e.conftest import BASE_URL


async def test_ws_connection_with_valid_token(api_context, registered_user):
    token = registered_user["token"]
    ws_url = f"ws://localhost:8000/api/ws?token={token}"

    # Playwright does not have a direct WebSocket client in the request API,
    # so we use the browser page's evaluate to open a WebSocket.
    page = await api_context.new_page()

    result = await page.evaluate(
        """(wsUrl) => {
            return new Promise((resolve) => {
                const ws = new WebSocket(wsUrl);
                ws.onopen = () => resolve({status: 'open'});
                ws.onerror = () => resolve({status: 'error'});
                ws.onclose = (e) => resolve({status: 'close', code: e.code});
                setTimeout(() => resolve({status: 'timeout'}), 5000);
            });
        }""",
        ws_url,
    )
    await page.close()

    assert result["status"] == "open", f"Expected open, got {result}"


async def test_ws_connection_with_invalid_token(api_context):
    ws_url = "ws://localhost:8000/api/ws?token=invalid_token_12345"
    page = await api_context.new_page()

    result = await page.evaluate(
        """(wsUrl) => {
            return new Promise((resolve) => {
                const ws = new WebSocket(wsUrl);
                ws.onopen = () => resolve({status: 'open'});
                ws.onerror = () => resolve({status: 'error'});
                ws.onclose = (e) => resolve({status: 'close', code: e.code});
                setTimeout(() => resolve({status: 'timeout'}), 5000);
            });
        }""",
        ws_url,
    )
    await page.close()

    # Should not succeed; either error or close with non-1000 code
    assert result["status"] != "open", f"Expected connection failure, got {result}"
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && pytest e2e/test_ws_e2e.py -v`
Expected: 2 passed (requires backend running)

- [ ] **Step 3: Commit**

```bash
git add backend/e2e/test_ws_e2e.py
git commit -m "test(e2e): add websocket e2e tests"
```

---

## Task 13: 全量回归测试

**Files:**
- Test: `backend/e2e/*.py`

- [ ] **Step 1: 运行全部 E2E 测试**

Run:
```bash
cd backend && pytest e2e/ -v --tb=short
```

Expected: 30+ tests passed, 0 failed

- [ ] **Step 2: 修复任何失败**

根据失败信息调整对应测试文件或 fixtures。常见修复点：
- Swagger UI 截图路径不存在 → `mkdir -p backend/e2e/screenshots`
- API 响应字段名变化 → 调整断言中的字段名
- `registered_user` fixture 中 family_id 可能不存在 → 改为 `body["data"]["member"].get("family_id")`

- [ ] **Step 3: 最终 Commit**

```bash
git add -A
git commit -m "test(e2e): complete Playwright E2E coverage for all 15 API modules"
```

---

## 自我审查

### 1. Spec 覆盖检查

| 设计文档要求 | 对应任务 |
|-------------|---------|
| 新增 `conftest.py` 统一 fixtures | Task 1 |
| 改造现有 8 个测试文件 | Task 2~5 |
| 补齐 auth 模块 | Task 6 |
| 补齐 home 模块 | Task 7 |
| 补齐 health_events 模块 | Task 8 |
| 补齐 medications 模块 | Task 9 |
| 补齐 export 模块 | Task 10 |
| 补齐 summary 模块 | Task 11 |
| 补齐 ws 模块 | Task 12 |
| 全量回归验证 | Task 13 |

**无缺口。**

### 2. Placeholder 扫描

- 无 TBD/TODO
- 无 "implement later"
- 无 "add appropriate error handling"
- 无 "similar to Task N"
- 每个代码步骤都包含完整代码

### 3. 类型一致性检查

- `registered_user` 返回 dict 含 `token`, `member_id`, `family_id`, `name` — 所有任务一致使用
- `auth_headers` 返回 dict 含 `Authorization` 和 `Content-Type` — 所有任务一致使用
- `BASE_URL` 统一从 `e2e.conftest` 导入 — 所有任务一致
- `swagger_page` 是 Playwright `Page` 对象 — 所有 Swagger 测试一致使用

### 4. 额外注意事项

- `test_ws_e2e.py` 使用 `page.evaluate` 在浏览器中运行 WebSocket，这是 Playwright 测试 WebSocket 的推荐方式。
- `test_report_e2e.py` 中 multipart upload 保持原有实现，使用 `Authorization` header 而非 `auth_headers` dict（因为 multipart 不需要 Content-Type: application/json）。
- `api_context` 在 `conftest.py` 中是 session scope，但在测试中通过 `registered_user` fixture 创建的每个用户是 function scope，确保测试隔离。
