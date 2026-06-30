# Care Assist 剩余任务实施方案

## 目标

补齐产品主流程与关键体验缺口，使项目从「功能可用」升级到「可内测/接近上线」。

本轮聚焦 4 个高优先级任务：

1. **B01 + B12：默认启用 Kimi OCR，上传后自动触发 AI 摘要**
2. **F05：慢性病专区多指标趋势图**
3. **F07：AI 回答 5 层结构化输出**
4. **B05：推送通知服务闭环**

要求：先写方案 → 拆分任务 → TDD 开发 → 集成测试验证。

---

## 任务 1：默认启用 Kimi OCR + 上传后自动 AI 摘要

### 当前问题

- `OCR_PROVIDER` 默认仍是 `mock`，真实报告无法识别。
- 上传页面只触发 OCR，不触发 AI 摘要，结果页看不到解读。

### 技术方案

**后端**

1. 将 `Settings.OCR_PROVIDER` 默认值改为 `"kimi"`。
2. 在 `uploadImage` 流程中，OCR 完成后自动调用 `AIService.summarize_report(report_id)`。
3. 保持失败安全：OCR 或摘要失败不影响报告创建，前端仍可展示原始结果。

**前端**

1. `pages/upload/upload.js` 在 OCR 成功后调用 `/api/reports/{id}/ai-summary`。
2. 结果页展示 `ai_summary`，失败时展示「暂未生成 AI 摘要」提示。

### TDD 策略

- 先写集成测试 `test_upload_auto_summary.py`：上传图片 → OCR → 摘要，断言 `report.ai_summary` 非空。
- 再写 `test_ocr_default_provider.py`：不设置 `OCR_PROVIDER` 时 `get_ocr_provider()` 返回 `KimiOCRProvider`。
- 最后实现代码。

---

## 任务 2：慢性病专区多指标趋势图

### 当前问题

- `pkg-system/pages/chronic/chronic.js` 详情页只有指标列表，无时间趋势。
- `components/trend-bottom-sheet` 已存在但未接入。

### 技术方案

**后端**

1. 新增 `/api/indicators/chronic/{package}/trend?member_id=xxx&days=180`。
2. 返回该慢性病包涉及的所有指标在最近 N 天的记录序列，每个点含 `recorded_at`、`value`、`status`。
3. 复用 `IndicatorEngine.get_threshold` 计算状态。

**前端**

1. 在慢病详情页顶部添加「趋势」入口或默认展开趋势图。
2. 用已有 `trend-bottom-sheet` 组件展示多指标折线。
3. 不同指标用不同颜色，支持显示/隐藏某条线。

### TDD 策略

- 先写 `test_chronic_trend.py`：为某成员创建多个血压/血糖记录，调用 trend API，断言返回多条序列且按时间排序。
- 再实现后端 API。
- 最后接入前端组件并补充前端单元/真机验证（无自动化则人工验证编译）。

---

## 任务 3：AI 回答 5 层结构化输出

### 当前问题

- AI 输出纯文本，前端只能做简单正则/追加，无法渲染卡片、建议、追问。

### 技术方案

**后端**

1. 新增 schema `AIResponse`：
   - `answer`: str 直接回答
   - `data_cards`: list[DataCard] 数据卡片
   - `suggestions`: list[str] 建议列表
   - `follow_up_questions`: list[str] 追问
   - `disclaimer`: str 免责声明
2. 新增 `AIService.chat_structured(messages)`，Prompt 强制模型按 JSON Schema 输出。
3. 新增 `/api/ai/structured` 端点（保留原 `/api/ai/chat` 兼容）。
4. 数据卡片根据当前成员指标/报告动态生成上下文。

**前端**

1. `pages/ai/ai.js` 调用新端点。
2. 渲染 5 层结构：直接回答文本、卡片网格、建议列表、可点击追问、底部免责声明。

### TDD 策略

- 先写 `test_ai_structured_response.py`：mock LLM 返回固定 JSON，断言端点返回 5 层字段。
- 再实现 `AIService.chat_structured` 和 API。
- 最后前端渲染，并验证空字段/异常 JSON 的兜底。

---

## 任务 4：推送通知服务闭环

### 当前问题

- Celery 已扫描漏服/逾期并生成 `Reminder`，但不会真正推送。
- 前端未调用 `wx.requestSubscribeMessage`。

### 技术方案

**后端**

1. 在 `ReminderEngine` 生成 `Reminder` 后，异步调用 `WechatService.send_subscribe_message(...)`。
2. 模板消息字段：`thing1`（提醒标题）、`time2`（计划时间）、`thing4`（成员名）。
3. 兜底：推送失败只记录日志，不影响主流程。
4. 新增 `/api/reminders/subscribe` 接收前端 `template_ids` 订阅记录（可选，存储到 `member` 或新表）。

**前端**

1. 在用药/疫苗/提醒相关页面，于关键操作后调用 `wx.requestSubscribeMessage` 申请一次性订阅。
2. 将订阅结果回传后端。

### TDD 策略

- 先写 `test_reminder_push.py`：创建逾期疫苗记录 → 调用 scan → mock 微信服务 → 断言 `send_subscribe_message` 被调用且参数正确。
- 再实现 ReminderEngine 推送钩子。
- 最后前端订阅授权与后端对接。

---

## 集成测试验证

全部任务完成后执行：

```bash
cd backend
DATABASE_URL="mysql+aiomysql://root@localhost:3308/care_assist" .venv/bin/python -m pytest -q
.venv/bin/ruff check app tests --output-format=concise
```

目标：
- 全量 pytest 通过（380+ passed, 0 failed）
- ruff 无新增错误
- 新增集成测试覆盖 4 个任务

## 执行状态

- [x] Task 1：默认 Kimi OCR + 上传自动 AI 摘要
- [x] Task 2：慢性病多指标趋势图
- [x] Task 3：AI 5 层结构化输出
- [x] Task 4：推送通知闭环
- [x] 集成测试验证：389 passed, 1 skipped；新增/修改文件 ruff 通过
