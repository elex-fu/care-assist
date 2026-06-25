# Care Assist 迭代计划清单 v2.1

> 基于当前代码实现与设计稿的深入差距分析
> 版本：v2.1 | 日期：2026-06-25 | 状态：持续迭代
>
> v2.1 更新：已接入 Kimi Code 真实 AI Provider，后端 AI 对话从规则模拟升级为真实模型调用。

---

## 一、文档说明

### 1.1 目标

本文档基于项目当前实现（微信小程序原生前端 + FastAPI 后端）与《家庭智能健康助手》系列设计稿的对比分析，系统梳理：

1. 已实现的能力与质量
2. 与设计稿相比仍缺失或不完善的能力
3. 按优先级和依赖关系排序的迭代任务清单
4. 前后端分工建议与关键验收标准

### 1.2 参考设计稿

| 文档 | 路径 | 主要内容 |
|------|------|----------|
| 家庭健康档案设计文档 | `Kimi_Agent_住院指标交互评估/design/design.md` | 产品核心能力、信息架构、关键页面定义 |
| 住院场景专项设计 v2.0 | `Kimi_Agent_住院指标交互评估/design/hospital-scenario.md` | 住院总览、指标盯盘、对比视图、批次检查单 |
| 系统产品设计文档 | `Kimi_Agent_住院指标交互评估/design/家庭智能健康助手_系统产品设计.md` | 技术架构、数据模型、API、业务规则、边界情况 |
| 前端设计规范 | `docs/design/frontend_design.md` | 页面规范、组件规范、趋势图、浮层组件 |
| 功能 UI 设计 | `docs/design/functional_ui_design.md` | 组件圆角、全局组件、成员卡片、空态设计 |

### 1.3 当前技术栈

- **前端**：原生微信小程序（`miniprogram/`），已使用分包（pkg-child / pkg-hospital / pkg-medication / pkg-system）
- **后端**：FastAPI + SQLAlchemy async + MySQL（aiomysql）+ Redis（连接池已配置但未使用）
- **部署**：Docker + docker-compose，开发环境 API Base 写死 `http://localhost:8000`

---

### 1.4 v2.1 更新记录

| 日期 | 变更项 | 影响 |
|------|--------|------|
| 2026-06-25 | 接入 Kimi Code 真实 AI Provider | 后端差距 **B02 真实 AI LLM** 已完成；P0-1 标记为已完成 |
| 2026-06-25 | 新增 `backend/app/ai/` Provider 抽象层 | 后续可低成本接入 OpenAI/Claude/DeepSeek/Qwen |
| 2026-06-25 | 测试配置自动禁用真实 AI Provider | 单元/集成测试在无 key 环境下可稳定运行 |

---

## 二、当前实现总览

### 2.1 前端页面地图

```
pages/
  index/          # 启动页：token 检查 → 引导/登录/首页
  onboarding/     # 首次引导（待确认完整度）
  login/          # 微信登录
  home/           # 首页：家庭看板 + AI日报 + 成员卡片网格
  indicators/     # 指标页：成员选择器 + 指标列表 + 添加指标 + 趋势弹窗
  upload/         # 上传：选成员 → 拍照/相册 → 预览 → 上传 → OCR → 结果
  ai/             # AI对话：成员选择器 + 聊天 + 快捷问题 + 历史
  profile/        # 我的：功能入口 + 成员管理 + 长辈模式开关
  member-add/     # 添加成员
  member-detail/  # 成员详情：时间轴/指标/报告/AI Tab
  invite/         # 邀请家人
  join/           # 加入家庭
  profile-edit/   # 编辑资料
  search/         # 搜索
  reports/        # 报告列表
  annual-summary/ # 年度汇总
  indicator-detail/ # 指标详情 + canvas 趋势图

pkg-hospital/     # 住院分包
  hospital/           # 住院记录列表
  hospital-add/       # 新增住院
  hospital-detail/    # 住院详情：每天情况/关键指标/对比变化

pkg-child/        # 儿童分包
  child-dashboard/    # 儿童档案首页（按龄段静态模板）
  vaccine/            # 疫苗列表
  vaccine-add/        # 添加疫苗

pkg-medication/   # 用药分包
  medication/         # 用药列表
  medication-add/     # 添加用药

pkg-system/       # 系统分包
  reminder/           # 提醒列表
  reminder-add/       # 添加提醒
  reminder-settings/  # 提醒设置
  export/             # 数据导出
  report-detail/      # 报告详情
  indicator-batch/    # 批量添加指标
```

### 2.2 前端组件

| 组件 | 状态 | 说明 |
|------|------|------|
| `member-card` | ✅ | grid/list/header 三种变体，已修复 `computeAge` 在 methods 中的问题 |
| `indicator-row` | ✅ | 指标行，支持 compact / trend |
| `timeline-node` | ✅ | 时间轴节点，8 种事件类型图标 |
| `abnormal-guide` | ✅ | 异常引导浮层，按 high/low/critical 生成行动 |
| `empty-state` | ✅ | 空态组件 |
| `lazy-image` | ✅ | 懒加载图片 |
| `report-card` | ✅ | 报告卡片 |

### 2.3 后端 API 地图

| 模块 | 路由 | 覆盖度 |
|------|------|--------|
| 认证 | `/api/auth/*` | ✅ login/register/refresh |
| 成员 | `/api/members/*` | ✅ CRUD + 邀请/加入/导出 |
| 首页 | `/api/home/dashboard` | ✅ 家庭+成员+AI摘要 |
| 指标 | `/api/indicators/*` | ✅ CRUD + batch + trend |
| 报告 | `/api/reports/*` | ✅ 上传 + OCR 触发 |
| 住院 | `/api/hospital-events/*` | ✅ CRUD + watch + compare |
| 疫苗 | `/api/vaccines/*` | ✅ CRUD |
| 提醒 | `/api/reminders/*` | ✅ CRUD |
| 健康事件 | `/api/health-events/*` | ✅ CRUD |
| AI 对话 | `/api/ai-conversations/*` | ✅ CRUD + WebSocket |
| 用药 | `/api/medications/*` | ✅ CRUD + take |
| 导出 | `/api/export/*` | ✅ Excel/PDF/JSON |
| 搜索 | `/api/search` | ✅ 多类型全文搜索 |
| 年度汇总 | `/api/summary/annual` | ✅ |

### 2.4 数据模型

已覆盖：Family、Member、IndicatorData、Report、HealthEvent、HospitalEvent、VaccineRecord、Reminder、Medication、MedicationLog、AIConversation。

---

## 三、设计稿核心能力清单

### 3.1 产品核心能力

1. **家庭多成员管理**：创建者邀请、被邀请人一键加入、角色权限
2. **智能病例/报告录入**：拍照 → AI 多模态识别 → 结果解读 → 一键提醒
3. **指标中心**：列表视图 + 表单视图（日期×指标透视表）+ 趋势图 + 异常标红
4. **慢性病专区**：高血压/糖尿病/高血脂套餐 + 多指标叠加趋势 + AI 简报
5. **AI 健康助手**：全局悬浮球 + 页面级问 AI + 主动推送 + 5 层回答结构
6. **时间轴首页**：纵向时间轴、3 色节点、筛选、住院特殊节点
7. **住院场景**：总览/盯盘/对比/批次检查单、长期住院聚合视图
8. **儿童健康专区**：13 个子模块、按龄动态显示、疫苗、成长曲线、里程碑预警
9. **用药管理**：当前用药、打卡日历、漏服提醒、添加用药浮层
10. **数据导出**：一键导出/精细选择、进度条、Excel/PDF

### 3.2 关键页面定义

| 页面编号 | 页面 | 设计稿状态 |
|----------|------|------------|
| P1 | 首页（家庭看板） | ✅ 已定义 |
| P2 | 指标页 | ✅ 已定义 |
| P3 | 我的页 | ✅ 已定义 |
| P4 | 成员详情 | ✅ 已定义 |
| P5 | 儿童档案 | ✅ 已定义 |
| P6 | 住院页 | ✅ 已定义 |
| P7 | 上传流程 | ✅ 已定义 |
| P8 | AI 对话 | ✅ 已定义 |
| P9 | 异常引导 | ✅ 已定义 |
| P10 | 首次引导 | ✅ 已定义 |
| P11 | 数据导出 | ✅ 已定义 |
| P12 | 家庭邀请 | ✅ 已定义 |
| P13 | 长辈模式 | ✅ 已定义 |
| P14 | 用药管理 | ✅ 已定义 |
| P15 | 手动录入 | ✅ 已定义 |

### 3.3 非功能性要求

- 性能：首页 < 2s、时间轴 < 3s、AI 响应 < 5s、OCR < 10s
- 安全：HTTPS、AES-256、家庭隔离、审计日志、限流
- 边界：空态/错误态/加载态、危险操作确认
- 埋点：page_view、upload_success、ai_chat_message 等 20+ 事件
- 推送：每日摘要、紧急提醒、复查提醒、疫苗到期等

---

## 四、已实现能力清单

### 4.1 前端已实现

| 能力 | 实现位置 | 完成度 |
|------|----------|--------|
| 原生微信小程序框架 | `miniprogram/` | ✅ 100% |
| 底部 5Tab 导航 | `app.json` | ✅ 100% |
| 首页家庭看板 | `pages/home/` | ✅ 80% |
| 成员卡片组件 | `components/member-card/` | ✅ 90% |
| 指标列表与添加 | `pages/indicators/` | ✅ 80% |
| 指标详情与趋势图 | `pages/indicator-detail/` | ✅ 75% |
| 上传与 OCR 流程 | `pages/upload/` | ✅ 70% |
| AI 对话页面 | `pages/ai/` | ✅ 70% |
| 成员详情 4Tab | `pages/member-detail/` | ✅ 75% |
| 时间轴节点 | `components/timeline-node/` | ✅ 80% |
| 异常引导浮层 | `components/abnormal-guide/` | ✅ 70% |
| 住院记录与详情 | `pkg-hospital/` | ✅ 65% |
| 用药管理 | `pkg-medication/` | ✅ 60% |
| 儿童档案首页 | `pkg-child/pages/child-dashboard/` | ✅ 40% |
| 疫苗记录 | `pkg-child/pages/vaccine/` | ✅ 60% |
| 数据导出 | `pkg-system/pages/export/` | ✅ 65% |
| 搜索页 | `pages/search/` | ✅ 待确认 |
| 长辈模式样式覆盖 | `app.wxss` | ✅ 50% |
| 骨架屏样式 | `app.wxss` | ✅ 70% |

### 4.2 后端已实现

| 能力 | 实现位置 | 完成度 |
|------|----------|--------|
| FastAPI 框架与路由 | `app/main.py` | ✅ 100% |
| 认证与 JWT | `app/core/security.py` | ✅ 90% |
| 权限控制 | `app/core/permissions.py` | ✅ 80% |
| 成员与家庭管理 | `app/api/members.py` | ✅ 85% |
| 指标异常判断引擎 | `app/core/indicator_engine.py` | ✅ 75% |
| 指标趋势评价 | `app/core/indicator_engine.py` | ✅ 70% |
| 报告上传与 OCR 触发 | `app/api/reports.py` | ✅ 70% |
| 住院 watch/compare | `app/api/hospitals.py` | ✅ 75% |
| AI 对话 REST + WebSocket | `app/api/ai_conversations.py`, `app/api/ws.py` | ✅ 85% |
| Kimi Code Provider | `app/ai/kimi_code_provider.py` | ✅ 90% |
| 用药 CRUD + take | `app/api/medications.py` | ✅ 75% |
| 导出 Excel/PDF/JSON | `app/services/export_service.py` | ✅ 75% |
| 搜索 | `app/api/search.py` | ✅ 60% |
| 单元/集成/E2E 测试 | `tests/`, `e2e/` | ✅ 75% |

---

## 五、差距分析：未实现 / 待完善能力

### 5.1 前端差距

| 编号 | 能力 | 设计稿要求 | 当前状态 | 差距等级 |
|------|------|------------|----------|----------|
| F01 | 全局 AI 悬浮球 | 56×56px 可拖拽紫色悬浮球，常驻所有页面 | 完全缺失 | 🔴 P0 |
| F02 | 首页最近查看快捷入口 | 3 槽位最近查看 | 完全缺失 | 🟡 P1 |
| F03 | 指标中心表单视图 | 日期×指标透视表，异常标红 | 仅有列表视图 | 🔴 P0 |
| F04 | 多指标叠加趋势 | Bottom Sheet 支持多指标对比 | 单指标趋势页面 | 🟡 P1 |
| F05 | 慢性病专区 | 高血压/糖尿病/高血脂套餐视图 | 完全缺失 | 🔴 P0 |
| F06 | AI 快捷问题动态生成 | 根据页面上下文和成员类型生成 2-4 个问题 | 静态 4 个问题 | 🟡 P1 |
| F07 | AI 回答 5 层结构 | 直接回答 → 数据 → 卡片 → 建议 → 追问 | 部分结构化解析 | 🟡 P1 |
| F08 | AI 半屏浮层 → 全屏 | Bottom Sheet 交互 | 独立页面 | 🟡 P1 |
| F09 | 趋势图 Bottom Sheet | 底部滑出趋势图 | 页面跳转 | 🟡 P1 |
| F10 | 住院批次检查单 | 按 AI 识别分组、异常置顶、灵活分组校正 | 缺失 | 🟡 P2 |
| F11 | 住院长期聚合视图 | 按天/周/月聚合（ICU 数月场景） | 缺失 | 🟡 P2 |
| F12 | 儿童成长曲线 | WHO 百分位标准身高/体重/头围/BMI | 缺失 | 🔴 P0 |
| F13 | 儿童发育里程碑 | 5 大类里程碑 + 落后预警 | 缺失 | 🟡 P1 |
| F14 | 儿童 13 个子模块 | 疫苗、营养、疾病咨询等按龄动态 | 仅疫苗+静态待办 | 🔴 P0 |
| F15 | 用药打卡日历 | 7 天视图，绿色/黄色状态 | 缺失 | 🟡 P1 |
| F16 | 用药添加浮层 | 药名联想、剂量、频率胶囊、时间多选 | 基础表单 | 🟡 P1 |
| F17 | 提醒自动触发 UI | 疫苗到期、复查、用药提醒的展示与完成 | 仅 CRUD | 🟡 P1 |
| F18 | 首次引导 4 步 | 添加成员 → 拍照 → AI 解读 → 开启提醒 | 待确认 | 🟡 P1 |
| F19 | 长辈模式完整适配 | 单成员聚焦、3Tab、语音输入优先 | 仅字体/按钮放大 | 🟡 P2 |
| F20 | 全局网络错误态 | 顶部黄色横幅 + 缓存数据 + 禁用上传/AI | 基础 toast | 🟡 P2 |
| F21 | 空态组件全覆盖 | 所有页面按设计稿空态 | 部分覆盖 | 🟡 P2 |
| F22 | 加载态骨架屏 | 首页/时间轴/指标中心等骨架屏 | 首页已做，其他待补 | 🟡 P2 |
| F23 | 上传失败兜底 | OCR 失败保留原图 + 手动录入入口 | 仅错误提示 | 🟡 P1 |
| F24 | 手动录入页 | OCR 失败替代路径、指标快捷选择、单位自动带出 | 缺失 | 🔴 P0 |
| F25 | 医疗免责声明常驻 | 首页 + AI 对话底部常驻 | 缺失 | 🟡 P2 |
| F26 | 埋点 SDK 接入 | 20+ 事件埋点 | 缺失 | 🟢 P3 |
| F27 | 推送通知订阅 | 微信订阅消息授权与接收 | 缺失 | 🟢 P3 |
| F28 | 分享打码 | 分享时自动打码非当前成员信息 | 缺失 | 🟢 P3 |

### 5.2 后端差距

| 编号 | 能力 | 设计稿要求 | 当前状态 | 差距等级 |
|------|------|------------|----------|----------|
| B01 | 真实 OCR 服务 | 腾讯云/百度/阿里云 OCR 多模态识别 | Mock/Regex | 🔴 P0 |
| B02 | 真实 AI LLM | Claude/GPT/文心一言接入 | **已接入 Kimi Code（kimi-k2.6）** | ✅ 已完成 |
| B03 | 定时任务引擎 | APScheduler/Celery 扫描提醒、疫苗逾期、AI 摘要 | 缺失 | 🔴 P0 |
| B04 | 提醒自动触发 | 疫苗/复查/用药/体检到期自动创建提醒 | 仅手动 CRUD | 🔴 P0 |
| B05 | 推送通知服务 | 微信订阅消息发送 | 仅模板配置 | 🟡 P1 |
| B06 | 疫苗逾期自动计算 | 根据 scheduled_date 自动更新 overdue | 手动状态 | 🟡 P1 |
| B07 | 标准疫苗库 | 国家免疫规划 0-6 岁自动填充 | 缺失 | 🟡 P1 |
| B08 | 成长记录模块 | GrowthRecord 模型 + API | 完全缺失 | 🔴 P0 |
| B09 | 儿童里程碑数据 | 里程碑标准数据与预警算法 | 缺失 | 🟡 P1 |
| B10 | 用药未来日志计划 | 自动生成未来 MedicationLog | 缺失 | 🟡 P1 |
| B11 | 指标统计聚合 | 按周/月平均值、指标目标值 | 缺失 | 🟡 P1 |
| B12 | 报告 AI 摘要触发 | 上传后自动生成 AI 解读 | 缺失 | 🟡 P1 |
| B13 | 健康事件 abnormal_count | 自动计算异常数量 | 字段存在未更新 | 🟡 P2 |
| B14 | API 限流 | Redis 限流（如 30/分钟 AI） | CORS 允许所有 | 🟡 P2 |
| B15 | Redis 缓存使用 | 仪表盘 AI 摘要缓存 | 已配置未使用 | 🟡 P2 |
| B16 | 审计日志 | 操作审计表 | 缺失 | 🟢 P3 |
| B17 | 头像上传 | 直接上传 OSS | 仅支持外部 URL | 🟡 P1 |
| B18 | 消息通知表 | Notification 模型 | 缺失 | 🟡 P2 |
| B19 | 深度健康检查 | /health 检查 DB/Redis | 仅返回 ok | 🟡 P2 |
| B20 | 多环境配置 | dev/prod 分层配置 | 单 .env | 🟢 P3 |

### 5.3 跨端/架构差距

| 编号 | 能力 | 差距 | 优先级 |
|------|------|------|--------|
| A01 | API Base 环境化 | 写死 `http://localhost:8000` | 🔴 P0 |
| A02 | WebSocket 生产适配 | 需要 wss + 心跳稳定 | 🟡 P1 |
| A03 | OSS 直传签名 | 前端直接上传私有 Bucket | 🟡 P1 |
| A04 | 图片 CDN + 签名 URL | 7 天过期访问 | 🟡 P2 |
| A05 | 分包预加载 | 优化分包加载体验 | 🟡 P2 |
| A06 | 数据预加载与缓存策略 | 首页/指标离线可用 | 🟡 P2 |

---

## 六、迭代计划清单

### 6.1 优先级说明

- **P0（阻断型）**：影响核心用户体验或产品主流程，必须优先补齐
- **P1（重要型）**：设计稿明确要求的能力，缺失会导致功能不完整
- **P2（体验型）**：边界情况、性能、长辈模式等体验优化
- **P3（增强型）**：埋点、审计、多环境等运维/运营能力

---

### 6.2 P0 迭代任务

#### P0-1 打通真实 AI 对话（前端 + 后端）✅ 已完成

**状态**：已完成 Kimi Code（kimi-k2.6）接入，后端 AI 对话已升级为真实模型调用。

**已实现**：
- 后端：新增 `app/ai/` Provider 抽象层，`KimiCodeProvider` 使用 Anthropic 协议调用 `https://api.kimi.com/coding/v1/messages`
- 后端：`AIService` 通过 `ProviderFactory` 路由到 Kimi Code，保留规则模拟作为 fallback
- 后端：支持非流式与流式（SSE）回复，已处理 Kimi Code 的 `data:{...}` 无空格 SSE 格式
- 配置：`backend/.env` 已配置真实 key（gitignored），`backend/.env.example` 提供示例
- 验证：`scripts/verify_kimi_code.py` 非流式/流式/家庭摘要均调用成功

**剩余优化**：
- AI 回答 5 层结构化输出（JSON Schema）+ 前端解析数据卡片/行动/追问（当前仍为文本解析）
- 多 Provider 故障降级（当前仅有 Kimi Code 一个 provider）
- 前端 AI 半屏浮层 → 全屏交互

**依赖**：B02 ✅、F07

---

#### P0-2 接入真实 OCR 报告识别（后端为主）

**问题**：当前 OCR 为 Mock/Regex，无法处理真实报告照片。

**任务**：
- 后端：`app/core/ocr_service.py` 接入腾讯云/百度/阿里云 OCR
- 后端：实现多 Provider  fallback
- 后端：OCR 后自动提取指标、判断异常、创建 IndicatorData
- 后端：OCR 失败保留原图并创建失败记录
- 前端：`pages/upload/upload.js` 增加 OCR 失败兜底提示和手动录入入口

**验收标准**：
- 真实检验报告图片能识别出指标名称、数值、单位、参考范围
- 识别准确率 > 80%
- 失败时保留原图并提示手动录入

**依赖**：B01、F23

---

#### P0-3 实现指标中心表单视图（前端为主）

**问题**：设计稿要求两种视图，当前仅列表视图。

**任务**：
- 前端：`pages/indicators/indicators.wxml` 增加视图切换（列表/表单）
- 前端：实现日期×指标透视表，异常单元格标红
- 后端：必要时提供 `/api/indicators/matrix?member_id=` 聚合接口

**验收标准**：
- 可在列表和表单视图间切换
- 表单视图行=日期，列=指标，异常标红
- 点击单元格可查看详情

**依赖**：F03

---

#### P0-4 建设慢性病专区（前端 + 后端）

**问题**：高血压/糖尿病/高血脂套餐视图完全缺失。

**任务**：
- 后端：`app/core/indicator_engine.py` 增加慢性病指标组合定义
- 后端：新增 `/api/indicators/chronic/{package}` 接口返回组合指标
- 后端：AI 生成慢性病管理简报
- 前端：新增 `pages/chronic/` 或 `pkg-system/pages/chronic/`
- 前端：慢性病套餐视图 + 多指标叠加趋势图

**验收标准**：
- 可查看高血压/糖尿病/高血脂套餐
- 套餐内多指标趋势可叠加对比
- AI 简报显示病情变化

**依赖**：F05、B12

---

#### P0-5 建设儿童成长与发育模块（前端 + 后端）

**问题**：儿童档案仅有静态待办和疫苗，成长曲线、里程碑、13 子模块缺失。

**任务**：
- 后端：新增 `GrowthRecord` 模型（身高/体重/头围/BMI/记录日期）
- 后端：新增 `/api/child/growth` CRUD 接口
- 后端：新增 `/api/child/milestones` 里程碑标准数据与预警
- 后端：新增 `/api/child/dashboard` 聚合儿童首页数据
- 前端：`pkg-child/pages/child-dashboard/` 按龄动态显示 13 子模块入口
- 前端：新增 `pkg-child/pages/growth/` 成长曲线（canvas 绘制 WHO 百分位）
- 前端：新增 `pkg-child/pages/milestone/` 发育里程碑

**验收标准**：
- 可记录儿童身高/体重/头围
- 自动生成 WHO 百分位曲线
- 里程碑落后时黄色/红色预警
- 首页按龄显示当前阶段关注事项

**依赖**：F12、F13、F14、B08、B09

---

#### P0-6 实现手动录入页（前端 + 后端）

**问题**：OCR 失败时无替代路径，设计稿要求手动录入。

**任务**：
- 后端：`/api/indicators` 支持更丰富的 indicator_key/name 映射
- 后端：指标同义词库 + 模糊匹配
- 前端：新增 `pages/manual-entry/` 或 `pkg-system/pages/indicator-manual/`
- 前端：常见指标快捷选择、搜索模糊匹配、自动带出单位和参考范围

**验收标准**：
- OCR 失败页可跳转手动录入
- 输入指标名时联想推荐
- 保存后自动判断异常

**依赖**：F24、B11

---

#### P0-7 API Base 环境化（前端）

**问题**：`app.js` 中写死 `http://localhost:8000`。

**任务**：
- 前端：`utils/api.js` 支持根据构建环境切换 API Base
- 前端：开发/测试/生产环境配置
- 文档：更新 SETUP.md

**验收标准**：
- 生产环境自动使用 HTTPS 域名
- 开发环境使用 localhost

**依赖**：A01

---

### 6.3 P1 迭代任务

#### P1-1 全局 AI 悬浮球（前端）

**任务**：
- 新增 `components/ai-fab/ai-fab`
- 可拖拽、松手回边界
- 点击展开 AI 对话 Bottom Sheet
- 所有页面（除登录/引导）全局可用

**验收标准**：
- 悬浮球在所有 Tab 页可见
- 拖拽流畅，松手有回弹动画
- 点击后可直接与 AI 对话

**依赖**：F01

---

#### P1-2 动态 AI 快捷问题（前端 + 后端）

**任务**：
- 后端：`/api/ai/quick-questions` 根据 page_context + member_type + 当前数据生成问题
- 前端：`pages/ai/ai.js`、`pages/member-detail/member-detail.js` 调用接口渲染快捷问题

**验收标准**：
- 儿童疫苗页显示疫苗相关问题
- 住院页显示住院相关问题
- 最多显示 2-4 个最相关问题

**依赖**：F06

---

#### P1-3 趋势图 Bottom Sheet 与多指标对比（前端）

**任务**：
- 新增 `components/trend-sheet/trend-sheet`
- 支持底部滑出、多指标叠加
- 指标中心/成员详情点击指标行时弹出
- 参考范围背景带、数据点交互

**验收标准**：
- 趋势图从底部滑出
- 可选择多个指标叠加
- 显示参考范围带

**依赖**：F04、F09

---

#### P1-4 用药打卡日历与漏服提醒（前端 + 后端）

**任务**：
- 后端：自动生成未来 MedicationLog
- 后端：`/api/medications/{id}/logs` 查询日志
- 后端：扫描漏服并创建提醒
- 前端：`pkg-medication/pages/medication/` 增加 7 天打卡日历
- 前端：标记服药/漏服状态

**验收标准**：
- 可查看 7 天用药记录
- 绿色=按时、黄色=漏服
- 漏服次日早上 8 点推送提醒

**依赖**：F15、F16、B10、B04

---

#### P1-5 提醒系统自动触发（后端 + 前端）

**任务**：
- 后端：APScheduler 定时扫描疫苗/复查/用药/体检到期
- 后端：自动创建/更新 Reminder 记录
- 后端：触发微信订阅消息推送
- 前端：`pkg-system/pages/reminder/` 显示待办/已完成/逾期

**验收标准**：
- 疫苗到期前 14 天自动生成提醒
- 复查提醒按异常等级生成 3/7 天提醒
- 用药提醒按时间生成

**依赖**：B03、B04、B05、F17

---

#### P1-6 标准疫苗库与逾期计算（后端 + 前端）

**任务**：
- 后端：内置国家免疫规划疫苗模板
- 后端：`/api/vaccines/seed` 为儿童自动填充计划
- 后端：定时扫描逾期状态
- 前端：疫苗页显示计划/已接种/逾期

**验收标准**：
- 添加儿童时可一键生成疫苗计划
- 逾期疫苗自动标红
- 到期前 14 天提醒

**依赖**：B06、B07

---

#### P1-7 报告 AI 摘要与一键提醒（后端 + 前端）

**任务**：
- 后端：上传报告后调用 AI 生成一句话解读
- 后端：`/api/reports/{id}/summary` 接口
- 前端：`pages/upload/upload.js` 结果页显示 AI 解读
- 前端：结果页增加「一键设置复查提醒」按钮

**验收标准**：
- 上传后显示 AI 一句话解读
- 可一键创建复查提醒

**依赖**：B12

---

#### P1-8 头像上传与 OSS 直传（后端 + 前端）

**任务**：
- 后端：`/api/upload/signature` 返回 OSS STS 临时凭证
- 后端：`app/services/oss_service.py` 生成签名 URL
- 前端：`pages/member-add/`、`pages/profile-edit/` 支持拍照上传头像

**验收标准**：
- 可上传头像到私有 Bucket
- 通过签名 URL 访问

**依赖**：B17、A03

---

### 6.4 P2 迭代任务

#### P2-1 首次引导 4 步流程（前端）

**任务**：
- 完善 `pages/onboarding/onboarding`
- 步骤：添加成员 → 拍照 → 看 AI 解读 → 开启提醒
- 强制引导新用户完成

**验收标准**：
- 新用户首次打开进入引导
- 4 步可完成并进入首页

**依赖**：F18

---

#### P2-2 长辈模式完整适配（前端）

**任务**：
- 首页单成员大图聚焦
- 底部 3Tab（首页/上传/我的）
- AI 悬浮球更大（72px）
- 语音输入优先
- 返回完整模式需连续点击 3 次

**验收标准**：
- 长辈模式下首页仅显示当前成员大图
- 5Tab 变为 3Tab
- 字体/按钮显著放大

**依赖**：F19

---

#### P2-3 全局错误态与网络处理（前端）

**任务**：
- `utils/api.js` 增加网络断开检测
- 顶部黄色横幅提示网络异常
- 弱网进度条与重试
- 上传/AI/OCR 时无网络禁用操作

**验收标准**：
- 网络断开时顶部显示横幅
- 缓存数据可查看
- 上传/AI 按钮禁用

**依赖**：F20

---

#### P2-4 空态与加载态全覆盖（前端）

**任务**：
- 所有页面补全 `empty-state`
- 所有列表页补全骨架屏
- 统一空态插画风格

**验收标准**：
- 首页无成员/有成员无数据均有空态
- 时间轴、指标中心、报告、住院、疫苗、用药均有骨架屏

**依赖**：F21、F22

---

#### P2-5 住院增强：批次检查单与长期聚合（前端 + 后端）

**任务**：
- 后端：`/api/hospital-events/{id}/batches` 按批次分组
- 后端：`/api/hospital-events/{id}/trend` 长期聚合
- 前端：`pkg-hospital/pages/hospital-detail/` 增加批次检查单 Tab
- 前端：长期住院按天/周/月聚合视图

**验收标准**：
- 可按批次查看检查单
- 异常指标置顶
- 长期住院可切换聚合粒度

**依赖**：F10、F11

---

#### P2-6 医疗免责声明常驻（前端）

**任务**：
- 首页底部常驻免责声明
- AI 对话底部常驻免责声明

**验收标准**：
- 首页可见「本应用仅供参考，不构成医疗建议」
- AI 对话每轮回复下方可见免责声明

**依赖**：F25

---

#### P2-7 后端限流与 Redis 缓存（后端）

**任务**：
- `app/middleware/rate_limit.py` 基于 Redis 的滑动窗口限流
- 关键接口限流：AI 30/分钟、上传 20/分钟、导出 5/分钟
- 仪表盘 AI 摘要缓存 1 小时

**验收标准**：
- 超出限流返回 429
- 首页 AI 摘要不重复生成

**依赖**：B14、B15

---

### 6.5 P3 迭代任务

#### P3-1 埋点 SDK 接入（前端）

**任务**：
- 接入微信自定义分析或自建埋点
- 实现 page_view、indicator_click、ai_chat_start、upload_success 等事件

**验收标准**：
- 20+ 核心事件可上报
- 上报成功率 > 95%

**依赖**：F26

---

#### P3-2 推送通知服务（后端 + 前端）

**任务**：
- 后端：微信 access_token 缓存与订阅消息发送
- 后端：每日摘要、紧急提醒、复查提醒、疫苗到期模板
- 前端：请求订阅消息授权

**验收标准**：
- 可收到每日健康摘要
- 严重异常实时推送（每小时最多 3 条）

**依赖**：B05、F27

---

#### P3-3 审计日志（后端）

**任务**：
- 新增 `AuditLog` 模型
- 中间件记录 who/when/what
- 保留 1 年

**验收标准**：
- 所有数据操作有审计记录
- 可查询最近 30 天操作日志

**依赖**：B16

---

#### P3-4 多环境配置（后端）

**任务**：
- 拆分 `config-dev.yaml` / `config-prod.yaml`
- 环境变量覆盖
- CI/CD 适配

**验收标准**：
- 生产环境不加载开发配置
- 敏感信息走环境变量

**依赖**：B20

---

#### P3-5 健康检查深度化（后端）

**任务**：
- `/health` 检查 DB、Redis 连通性
- 返回各依赖状态

**验收标准**：
- DB 不可用时返回 503
- Redis 不可用时标记为降级

**依赖**：B19

---

## 七、迭代路线图

### 第一阶段：核心能力补齐（4-6 周）

目标：让产品主流程达到设计稿 80% 完整度，可内测。

| 周 | 重点任务 |
|----|----------|
| 1 | P0-7 API Base 环境化、P1-1 AI 悬浮球、P2-4 空态/骨架屏补全 |
| 2 | ✅ P0-1 真实 AI（已完成 Kimi Code 接入）、P0-2 真实 OCR、P1-7 报告 AI 摘要 |
| 3 | P0-3 指标表单视图、P0-4 慢性病专区 |
| 4 | P0-6 手动录入、P1-3 趋势图 Bottom Sheet |
| 5 | P0-5 儿童成长模块、P1-6 标准疫苗库 |
| 6 | P1-4 用药打卡、P1-5 提醒自动触发、P0-1 剩余优化（结构化输出/多 Provider） |

### 第二阶段：体验与边界（3-4 周）

目标：完善长辈模式、错误态、首次引导、住院增强。

| 周 | 重点任务 |
|----|----------|
| 7 | P2-1 首次引导、P2-2 长辈模式 |
| 8 | P2-3 全局错误态、P2-6 医疗免责声明 |
| 9 | P2-5 住院批次检查单与聚合、P2-7 限流与缓存 |
| 10 | 全链路测试、性能优化 |

### 第三阶段：运营与合规（2-3 周）

目标：埋点、推送、审计、多环境、上线准备。

| 周 | 重点任务 |
|----|----------|
| 11 | P3-1 埋点、P3-2 推送通知 |
| 12 | P3-3 审计日志、P3-4 多环境配置 |
| 13 | P3-5 深度健康检查、安全审查、上线 |

---

## 八、风险与建议

### 8.1 主要风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 真实 OCR/AI 接入成本与合规 | 高 | 优先国内合规 Provider，先做 MVP 模型，逐步替换 |
| 医疗合规风险 | 高 | 全链路加入免责声明，AI 输出避免诊断性表述 |
| 儿童数据隐私 | 高 | 16 岁以下数据加密，分享需家长确认 |
| 微信小程序包体积 | 中 | 继续分包，图片走 CDN，canvas 趋势图代码精简 |
| 后端定时任务可靠性 | 中 | 使用 APScheduler + Redis 锁，避免多实例重复触发 |
| 测试环境 MySQL 端口不一致 | 低 | 已发现 3307/3308 问题，统一配置 |

### 8.2 关键建议

1. **先补齐 P0，再扩展 P1**：P0 是产品可用性的基础，P1 是完整度的提升。
2. **AI 与 OCR 优先**：这是产品差异化和核心价值所在。
3. **儿童模块单独一个迭代**：涉及数据模型、算法、大量前端页面，建议集中开发。
4. **前后端并行**：前端页面可以先使用 mock 数据，等待后端接口。
5. **加强测试**：每个 P0/P1 任务配套单元测试和集成测试，避免回归。
6. **文档同步**：每完成一个迭代更新本文档和 API 文档。

---

## 九、附录

### 9.1 关键文件索引

| 类型 | 文件 | 说明 |
|------|------|------|
| 前端入口 | `miniprogram/app.js` | 全局状态、API Base |
| 前端路由 | `miniprogram/app.json` | 页面与分包配置 |
| 前端样式 | `miniprogram/app.wxss` | CSS 变量、长辈模式、骨架屏 |
| API 封装 | `miniprogram/utils/api.js` | 请求、401 刷新、上传 |
| 全局状态 | `miniprogram/utils/store.js` | Proxy store |
| 后端入口 | `backend/app/main.py` | FastAPI 注册路由 |
| 指标引擎 | `backend/app/core/indicator_engine.py` | 异常判断、趋势评价 |
| AI 服务 | `backend/app/core/ai_service.py` | AI 回复路由（已接入 Kimi Code） |
| AI Provider 抽象 | `backend/app/ai/provider.py` | Provider 抽象接口 |
| Kimi Code Provider | `backend/app/ai/kimi_code_provider.py` | Kimi Code Anthropic 协议实现 |
| Provider 工厂 | `backend/app/ai/factory.py` | Provider 工厂与故障降级 |
| OCR 服务 | `backend/app/core/ocr_service.py` | OCR（待接入真实服务） |
| 权限 | `backend/app/core/permissions.py` | 角色权限 |

### 9.2 后续维护

- 每次迭代完成后，由负责人更新本清单中的「当前状态」与「完成度」
- 新增能力需先在设计稿中确认，再补充到差距分析表
- 每两周Review一次优先级，根据用户反馈调整 P1/P2 顺序

---

*本文档由 Claude Code 基于 2026-06-25 代码快照与设计稿对比分析生成。*
