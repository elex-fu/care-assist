# 开发实施计划

> 版本：v1.0 | 日期：2026-05-12 | 面向开发者的任务拆分

---

## 总览

| 阶段 | 主题 | 预估工期 | 可并行 |
|------|------|---------|--------|
| Phase 0 | 基础设施 | 已完成 | — |
| Phase 1 | 数据层 + 认证 | 3-4 天 | — |
| Phase 2 | 首页 + 成员管理（MVP） | 5-6 天 | — |
| Phase 3 | 指标中心 | 4-5 天 | — |
| Phase 4 | 报告上传 + OCR | 5-6 天 | Phase 3 并行部分 |
| Phase 5 | AI 对话 | 5-6 天 | Phase 3 并行部分 |
| Phase 6 | 住院管理 | 4-5 天 | — |
| Phase 7 | 儿童模块 | 3-4 天 | — |
| Phase 8 | 时间轴 + 提醒 | 4-5 天 | — |
| Phase 9 | 高级功能 | 4-5 天 | — |
| Phase 10 | 测试 + 优化 + 上线 | 5-6 天 | — |

**关键路径**：Phase 1 → Phase 2 → Phase 3/4/5 → Phase 8 → Phase 10

---

## Phase 0: 基础设施（已完成）

**交付物**：
- [x] 后端骨架：FastAPI + async SQLAlchemy + Alembic + Dockerfile
- [x] 前端骨架：微信小程序 `app.js/json/wxss` + 首页占位
- [x] 开发脚本：`dev-start.sh` / `dev-stop.sh` / `dev-status.sh`
- [x] 设计文档：5 份技术文档 + 工程评审修复

---

## Phase 1: 数据层 + 认证（3-4 天）

**目标**：所有数据库模型就绪，微信登录打通，用户可创建家庭并登录。

### 后端任务

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 1.1 | 定义全部 SQLAlchemy 模型 | `app/models/` | 9 张表：families, members, indicator_data, reports, hospital_events, health_events, reminders, ai_conversations, vaccine_records |
| 1.2 | Alembic 初始迁移脚本 | `alembic/versions/` | 生成并执行首版 DDL，创建全部表 + 索引 |
| 1.3 | 种子数据 | `app/db/seed.py` | 标准指标阈值字典（THRESHOLDS）、基础疫苗计划模板 |
| 1.4 | 微信登录 API | `app/api/auth.py` | `POST /api/auth/login`（wx.code → JWT）、`POST /api/auth/refresh` |
| 1.5 | JWT 依赖注入 | `app/core/security.py` | `get_current_member()`、token 刷新竞态锁（Promise lock 的后端配合） |
| 1.6 | 家庭成员关系 API | `app/api/members.py` | `POST /api/members/me`（完善资料）、`GET /api/members/me`、家庭创建/加入/邀请链 |
| 1.7 | 角色权限中间件 | `app/core/permissions.py` | creator / member 权限校验 decorator |

### 前端任务

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 1.8 | 微信登录页 | `pages/login/` | `wx.login` → 调用后端 login API → 存储 token |
| 1.9 | 首次使用引导 | `pages/onboarding/` | P10：创建家庭 → 添加第一个成员 → 完成引导 |
| 1.10 | 全局状态初始化 | `utils/store.js` | Proxy-based store：token、currentMember、family、members |
| 1.11 | API 请求封装完善 | `utils/api.js` | 401 刷新 Promise lock、统一错误处理、请求/响应拦截 |

### 数据库变更
- 9 张表全部创建
- 索引：`idx_family`、`idx_wx_openid`、`idx_member_indicator_date` 等

### 验收标准
- [ ] `./scripts/dev-start.sh` 启动后，Alembic 自动迁移完成
- [ ] 微信开发者工具中可完成登录流程，获得有效 JWT
- [ ] 创建家庭后，`GET /api/members/me` 返回正确的家庭信息
- [ ] 401 并发刷新测试通过（`refreshToken` 仅调用 1 次）

---

## Phase 2: 首页 + 成员管理（MVP 核心）（5-6 天）

**目标**：用户登录后看到家庭看板，可查看成员卡片、添加成员。这是产品最核心页面，必须先完成。

### 后端任务

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 2.1 | 成员卡片数据聚合 | `app/services/member_service.py` | 查询每个成员的最新指标、状态、异常数量 |
| 2.2 | 首页数据 API | `app/api/home.py` | `GET /api/home/dashboard`：返回家庭名称 + 成员卡片数组 + AI 日报摘要 |
| 2.3 | 邀请链接服务 | `app/services/member_service.py` | `generate_invite_link`、`join_by_link` |
| 2.4 | 图片上传签名 | `app/services/oss_service.py` | 生成阿里云 OSS 临时上传凭证（STS） |

### 前端任务

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 2.5 | 底部 5Tab 导航 | `app.json` + `custom-tab-bar/` | 首页/指标/上传/AI/我的，AI Tab 紫色凸起 |
| 2.6 | 首页 — 家庭看板 | `pages/home/` | P1：顶部家庭名称 + AI 图标 → AI 日报横幅 → 成员卡片网格（2列）→ TabBar |
| 2.7 | 成员卡片组件 | `components/member-card/` | 差异化显示：成人慢病/成人健康/儿童/住院中，不对称圆角 20/12/20/12 |
| 2.8 | 添加成员页 | `pages/member-add/` | 表单：姓名、关系、生日、性别、血型、过敏史、慢性病 |
| 2.9 | 成员详情页（基础） | `pages/member-detail/` | P4 基础版：顶部成员信息（头像、姓名、年龄、血型） |
| 2.10 | 家庭邀请页 | `pages/invite/` | P12：生成邀请码/链接、微信分享 |

### 数据库变更
- 无新增表（复用 Phase 1 模型）
- 可能需要 `families.invite_code` 索引

### 验收标准
- [ ] 登录后首页正确渲染 2 列成员卡片网格
- [ ] 添加成员后首页自动刷新，新成员卡片出现
- [ ] 成员卡片状态颜色正确（绿/黄/红 + 图标 + 文字）
- [ ] 邀请链接可被另一微信用户打开并成功加入家庭
- [ ] 长辈模式切换开关可用（简化导航为 3Tab）

---

## Phase 3: 指标中心（4-5 天）

**目标**：支持指标的手动录入、列表展示、趋势图、异常判断。

### 后端任务

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 3.1 | IndicatorEngine 异常判断 | `app/core/indicator_engine.py` | `standardize()`、`judge()`、`calculate_deviation()`、`evaluate_trend()` |
| 3.2 | 指标 CRUD API | `app/api/indicators.py` | `POST/GET/DELETE /api/indicators`、单成员/多成员查询 |
| 3.3 | 趋势查询 API | `app/api/indicators.py` | `GET /api/indicators/{member_id}/trend?key=bp_systolic&days=30` |
| 3.4 | 慢性病套餐逻辑 | `app/services/indicator_service.py` | 高血压/糖尿病/高血脂套餐，多指标聚合 |

### 前端任务

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 3.5 | 指标页 — 列表视图 | `pages/indicators/` | P2：指标卡片（名称+最新值+趋势箭头+状态Badge） |
| 3.6 | 趋势图 Bottom Sheet | `components/trend-chart/` | echarts-for-weixin 折线图，支持多指标叠加 |
| 3.7 | 手动录入指标页 | `pages/indicator-input/` | P15：表单录入（数值+单位+日期），支持血压双输入 |
| 3.8 | 表单视图（透视表） | `pages/indicators/form-view/` | 日期×指标透视表，异常数值红色高亮 |

### 数据库变更
- `indicator_data` 表写入测试数据
- `THRESHOLDS` 种子数据补全各年龄段阈值

### 验收标准
- [ ] 手动录入血压 128/82，保存后状态判断为「正常」或「偏高」
- [ ] 趋势图正确渲染最近 30 次记录
- [ ] 异常指标卡片显示黄色/红色，并带文字说明（如「血压高了一点」）
- [ ] 长辈模式下指标页字体放大、按钮增高

---

## Phase 4: 报告上传 + OCR（5-6 天）

**目标**：用户拍照上传报告，系统自动 OCR 识别并提取指标。

### 后端任务

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 4.1 | OSS 上传签名服务 | `app/services/oss_service.py` | STS 临时凭证、签名直传 URL |
| 4.2 | OCR Celery 任务修复 | `app/tasks/ocr_task.py` | `async_to_sync` 包装器、异步 body 正确执行 |
| 4.3 | AI 图像解析 | `app/ai/kimi_provider.py` | `analyze_image()`：医疗报告 OCR + 指标提取 |
| 4.4 | 报告管理 API | `app/api/reports.py` | `POST/GET /api/reports`、上传回调、OCR 状态轮询 |
| 4.5 | OCR 完成 WebSocket 推送 | `app/api/ws.py` | OCR 完成后通过 WS 推送给前端 |
| 4.6 | 报告与指标关联 | `app/services/report_service.py` | OCR 结果自动写入 `indicator_data` + `health_events` |

### 前端任务

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 4.7 | 上传流程页 | `pages/upload/` | P7：Step1 拍照 → Step2 确认 → Step3 上传中（骨架屏）→ 完成 |
| 4.8 | 上传状态监听 | `utils/ws.js` | WebSocket 接收 `ocr_completed` 消息，自动刷新指标列表 |
| 4.9 | 报告列表页 | `pages/reports/` | 按时间倒序展示报告缩略图 + OCR 状态 + 提取指标数 |
| 4.10 | 报告详情页 | `pages/report-detail/` | 原图 + 提取指标列表 + AI 解读摘要 |

### 依赖
- Phase 3 的指标录入逻辑（OCR 结果要写入 `indicator_data`）
- Phase 1 的 OSS 签名（图片上传）

### 验收标准
- [ ] 拍照上传后，前端显示「AI 识别中...」骨架屏
- [ ] OCR 完成后，WebSocket 推送消息，前端自动跳转到报告详情
- [ ] 报告详情页展示提取的指标，且已同步到成员指标列表
- [ ] OCR 失败时展示错误态 + 「手动录入」入口
- [ ] E2E 测试覆盖：upload → OCR → AI → DB → WS push 完整链路

---

## Phase 5: AI 对话（5-6 天）

**目标**：AI 助手可回答健康相关问题，支持流式输出和数据卡片。

### 后端任务

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 5.1 | AI Provider ABC + 实现 | `app/ai/provider.py`、`app/ai/kimi_provider.py` 等 | `chat()`、`analyze_image()`、`generate_summary()` |
| 5.2 | Provider 工厂 + 故障降级 | `app/ai/factory.py` | `ProviderFactory.get_provider()`、`chat_with_fallback()` |
| 5.3 | AI 对话上下文管理 | `app/services/ai_service.py` | SYSTEM_PROMPT、4 级上下文构建、历史消息截取 |
| 5.4 | AI 对话 REST API | `app/api/ai.py` | `POST /api/ai/chat`（非流式兜底） |
| 5.5 | WebSocket 流式对话 | `app/api/ws.py` | `handle_chat_stream`、逐 token 推送到前端 |
| 5.6 | AI 回答结构化 | `app/services/ai_service.py` | 5 层结构：直接回答 → 数据支撑 → 数据卡片 → 建议 → 追问推荐 |

### 前端任务

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 5.7 | AI 对话浮层 | `components/ai-chat/` | P8：半屏 → 上滑全屏，Markdown 渲染 + 数据卡片 |
| 5.8 | AI 悬浮球 | `components/ai-floating/` | 右下角可拖拽悬浮球，紫色渐变，sparkle 图标 |
| 5.9 | 快捷问题网格 | `components/ai-chat/quick-questions/` | 2×2 快捷问题，上下文自适应 |
| 5.10 | 数据卡片组件 | `components/ai-chat/data-card/` | 可点击指标卡片 → 跳转趋势图 |
| 5.11 | AI Tab 页面 | `pages/ai/` | 全屏对话页，与浮层共享同一面板 |

### 依赖
- Phase 1 的 WebSocket 连接管理（已完成骨架）
- Phase 3 的指标数据（AI 回答需要引用数据）

### 验收标准
- [ ] 点击悬浮球打开 AI 对话浮层，半屏显示
- [ ] 输入「我爸爸的血压怎么样」，AI 引用最新血压数据并给出建议
- [ ] 回答中包含可点击的数据卡片，点击后打开趋势图 Bottom Sheet
- [ ] 主 Provider 故障时自动降级到备用 Provider，用户无感知
- [ ] WS 连接断开后指数退避重连（最多 5 次）

---

## Phase 6: 住院管理（4-5 天）

**目标**：支持住院事件创建、每日记录、盯盘、对比。

### 后端任务

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 6.1 | HospitalService | `app/services/hospital_service.py` | 住院事件 CRUD、每日检查批次、指标对比、盯盘自选 |
| 6.2 | 住院管理 API | `app/api/hospitals.py` | `POST/GET/PUT /api/hospitals`、批次查询、对比查询 |
| 6.3 | 住院-指标关联 | `app/services/hospital_service.py` | 住院期间指标自动关联到住院事件 |
| 6.4 | 长期住院聚合 | `app/services/hospital_service.py` | 按天/周/月聚合，均值+范围+异常天数 |

### 前端任务

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 6.5 | 住院页面 | `pages/hospital/` | P6：顶部 Tab（总览/盯盘/对比/批次） |
| 6.6 | 住院总览 Tab | `pages/hospital/overview/` | 每日检查批次卡片纵向排列 |
| 6.7 | 盯盘 Tab | `pages/hospital/watch/` | 3 列卡片网格，自选任意数量指标 |
| 6.8 | 对比 Tab | `pages/hospital/compare/` | 任意两天对比，自动计算变化+评价 |
| 6.9 | 批次 Tab | `pages/hospital/batch/` | 灵活分组检查单，异常置顶 |
| 6.10 | 住院事件创建 | `pages/hospital-create/` | 医院、科室、入院日期、诊断 |

### 依赖
- Phase 3 的指标数据（住院盯盘需要指标）

### 验收标准
- [ ] 创建住院事件后，首页成员卡片显示「住院中」紫色 Badge
- [ ] 住院期间上传的报告，指标自动关联到住院事件
- [ ] 盯盘 Tab 可自选指标，3 列网格实时更新
- [ ] 对比 Tab 可对比任意两天，变化值带箭头+颜色

---

## Phase 7: 儿童模块（3-4 天）

**目标**：支持儿童档案、疫苗记录、成长里程碑。

### 后端任务

| # | 任务 | 文件 | 说明 |
|---|------|------|
| 7.1 | ChildService | `app/services/child_service.py` | 年龄分段布局配置、里程碑数据、疫苗计划 |
| 7.2 | 儿童管理 API | `app/api/child.py` | `GET /api/child/{member_id}/dashboard`、疫苗 CRUD、里程碑查询 |
| 7.3 | 疫苗提醒生成 | `app/services/reminder_service.py` | 根据疫苗计划自动创建提醒 |

### 前端任务

| # | 任务 | 文件 | 说明 |
|---|------|------|
| 7.4 | 儿童档案页 | `pages/child/` | P5：顶部年龄标签 → 动态内容区（疫苗/身高体重/里程碑） |
| 7.5 | 疫苗进度组件 | `components/vaccine-progress/` | 进度条 + 下次接种日期 + 到期警告 |
| 7.6 | 里程碑展示 | `components/milestones/` | 已达成/未达成里程碑列表 |
| 7.7 | 儿童数据隐私同意 | `components/child-privacy/` | Guardian 同意流程（14 岁以下） |

### 依赖
- Phase 2 的成员管理（儿童是成员的一种 type）

### 验收标准
- [ ] 儿童成员卡片显示疫苗进度% + 下次接种日期
- [ ] 疫苗到期前 7 天，成员卡片显示黄色⚠️角标
- [ ] 未同意隐私协议时，儿童数据不可被非 guardian 查看
- [ ] 里程碑按年龄自动筛选，已达成项绿色标记

---

## Phase 8: 时间轴 + 提醒系统（4-5 天）

**目标**：统一时间轴展示所有健康事件，智能提醒生成与推送。

### 后端任务

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 8.1 | health_events 统一时间轴 | `app/services/timeline_service.py` | 聚合：就诊/检验/用药/症状/AI解读/住院/疫苗/里程碑 |
| 8.2 | 时间轴查询 API | `app/api/timeline.py` | `GET /api/timeline?member_id=&type=&page=` |
| 8.3 | ReminderService | `app/services/reminder_service.py` | RULES 数组、`create_from_abnormal()`、定时任务 |
| 8.4 | 提醒管理 API | `app/api/reminders.py` | `GET/POST/PUT /api/reminders` |
| 8.5 | 微信订阅消息推送 | `app/services/wechat_service.py` | 调用微信服务端 API 发送订阅消息 |
| 8.6 | 每日待办推送 | `app/tasks/reminder_task.py` | Celery Beat 每日 8:00 执行 |

### 前端任务

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 8.7 | 成员详情页 — 时间轴 | `pages/member-detail/timeline/` | P4 完整版：筛选标签 + 纵向时间轴节点 |
| 8.8 | 时间轴节点组件 | `components/timeline-node/` | 8 种类型差异化显示（颜色/图标/高度） |
| 8.9 | 住院节点特殊设计 | `components/timeline-node/hospital/` | 紫色背景条跨越住院天数，高 40px |
| 8.10 | 提醒列表页 | `pages/reminders/` | 待办/已完成分类，过期红色标记 |
| 8.11 | 提醒设置 | `pages/reminders/settings/` | 订阅开关：日常摘要/紧急异常/复查提醒 |

### 依赖
- Phase 3/4/6/7 的数据源（指标、报告、住院、疫苗都会生成时间轴事件）

### 验收标准
- [ ] 上传报告后，时间轴新增「检验」节点（绿色）
- [ ] 指标异常后，时间轴新增「AI解读」节点（紫色）+ 提醒列表新增「复查提醒」
- [ ] 每日 8:00 收到微信订阅消息推送（测试环境可手动触发）
- [ ] 时间轴支持按类型筛选，空态显示温暖插画

---

## Phase 9: 高级功能（4-5 天）

**目标**：数据导出、家庭邀请完善、长辈模式、用药管理、设置页。

### 后端任务

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 9.1 | ExportService | `app/services/export_service.py` | openpyxl（Excel）、reportlab（PDF） |
| 9.2 | 数据导出 API | `app/api/export.py` | `POST /api/export/all?format=excel`、异步生成 + 下载链接 |
| 9.3 | 用药管理 API | `app/api/medications.py` | 用药记录 CRUD、用药提醒（可复用 reminder 表） |
| 9.4 | 长辈模式 API | `app/api/settings.py` | 模式切换、单成员聚焦视图数据过滤 |

### 前端任务

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 9.5 | 数据导出页 | `pages/export/` | P11：选择成员/时间范围/格式 → 生成 → 下载 |
| 9.6 | 家庭邀请完善 | `pages/invite/` | P12：邀请码过期机制、链接已使用检测 |
| 9.7 | 长辈模式设置 | `pages/settings/elderly/` | P13：单成员大图、大字体、语音输入、3Tab 简化 |
| 9.8 | 用药管理页 | `pages/medications/` | P14：用药列表、添加用药（名称/剂量/频率/时间）、用药提醒 |
| 9.9 | 我的页 — 完整版 | `pages/profile/` | P3：家庭管理、成员列表、设置、关于、退出登录 |
| 9.10 | 异常引导浮层 | `components/abnormal-guide/` | P9：指标异常时的行动建议浮层 |

### 验收标准
- [ ] 导出 Excel 包含所有指标数据，格式正确
- [ ] 长辈模式切换后首页变为单成员大图，字体 20px+
- [ ] 用药提醒到期时，微信推送通知
- [ ] 设置页可管理家庭成员、修改订阅偏好

---

## Phase 10: 测试 + 优化 + 上线（5-6 天）

**目标**：全面测试、性能优化、准备上线。

### 测试任务

| # | 任务 | 说明 |
|---|------|------|
| 10.1 | 单元测试补齐 | pytest ≥ 80%，重点：IndicatorEngine、Auth、权限、Service 层 |
| 10.2 | 集成测试 | pytest + TestClient ≥ 60%，API 路由、数据库事务 |
| 10.3 | E2E 核心路径 | Minium：登录 → 添加成员 → 上传报告 → OCR → 查看指标 → AI 对话 |
| 10.4 | 401 竞态回归测试 | 模拟 3 并发 401，断言 1 次 refresh |
| 10.5 | OCR 链路 E2E | mock 外部服务，验证每个失败分支 |
| 10.6 | AI Prompt 回归 | 黄金数据集，OCR 准确率 ≥ 80% |
| 10.7 | 无障碍测试 | VoiceOver/TalkBack 读屏顺序、aria-label 正确性 |

### 优化任务

| # | 任务 | 说明 |
|---|------|------|
| 10.8 | 性能优化 | 首页加载 < 2s、AI 响应 < 5s、图片懒加载、列表虚拟滚动 |
| 10.9 | 分包优化 | 按业务分包（member/hospital/child），主包 < 2MB |
| 10.10 | 弱网适配 | 离线队列、请求重试、骨架屏、超时处理 |
| 10.11 | 数据清理验证 | 分批删除策略在生产数据上验证 |

### 上线准备

| # | 任务 | 说明 |
|---|------|------|
| 10.12 | 微信小程序审核材料 | 隐私政策、用户协议、医疗资质（如需要） |
| 10.13 | 生产环境部署 | Nginx + FastAPI 多实例 + MySQL 主从 + Redis Sentinel + OSS CDN |
| 10.14 | 监控接入 | Sentry 错误追踪、日志聚合、核心指标监控 |
| 10.15 | 灰度发布 | 先内部测试 → 小范围用户 → 全量 |

---

## 附录：依赖关系图

```
Phase 0 (基础设施)
    │
    ▼
Phase 1 (数据层 + 认证)
    │
    ├──► Phase 2 (首页 + 成员管理) ──┐
    │                                │
    ├──► Phase 3 (指标中心) ◄────────┤
    │       ▲                        │
    │       │                        │
    ├──► Phase 4 (上传 + OCR) ───────┤
    │       │                        │
    ├──► Phase 5 (AI 对话) ◄─────────┤
    │                                │
    ├──► Phase 6 (住院管理) ◄────────┘
    │       │
    ├──► Phase 7 (儿童模块)
    │
    ├──► Phase 8 (时间轴 + 提醒) ◄─── 依赖 Phase 3/4/6/7
    │
    └──► Phase 9 (高级功能)
            │
            ▼
    Phase 10 (测试 + 优化 + 上线)
```

---

## 附录：各阶段 API 与数据库对照

| 阶段 | 新增 API 模块 | 新增/主要使用表 |
|------|--------------|----------------|
| Phase 1 | `/api/auth`、`/api/members` | families, members |
| Phase 2 | `/api/home`、`/api/oss` | families, members |
| Phase 3 | `/api/indicators` | indicator_data |
| Phase 4 | `/api/reports` | reports, indicator_data, health_events |
| Phase 5 | `/api/ai`、`/ws` | ai_conversations |
| Phase 6 | `/api/hospitals` | hospital_events, indicator_data |
| Phase 7 | `/api/child` | vaccine_records, members |
| Phase 8 | `/api/timeline`、`/api/reminders` | health_events, reminders |
| Phase 9 | `/api/export` | 全表查询 |
| Phase 10 | — | — |
