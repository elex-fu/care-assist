# 家庭智能健康助手 — 技术架构方案

> 版本：v1.0 | 日期：2026-05-08 | 读者：技术负责人 / 架构师 / 项目经理 | 状态：设计定稿

---

## 目录

1. [系统架构总览](#一系统架构总览)
2. [前端架构设计](#二前端架构设计)
3. [后端架构设计](#三后端架构设计)
4. [关键模块设计](#四关键模块设计)
5. [数据库设计概览](#五数据库设计概览)
6. [部署与运维](#六部署与运维)
7. [安全方案](#七安全方案)
8. [测试策略](#八测试策略)
9. [数据生命周期管理](#九数据生命周期管理)

---

## 一、系统架构总览

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        客户端层                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              微信小程序（原生SDK）                     │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │   │
│  │  │  首页   │ │  指标   │ │   AI    │ │  上传   │ │   我的   │  │   │
│  │  │ (首页)  │ │(趋势入口)│ │(对话页) │ │(拍照页) │ │(设置)   │  │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │   │
│  │  │成员详情 │ │指标中心 │ │住院专页 │ │儿童专区 │  │   │
│  │  │(子包)   │ │(子包)   │ │(子包)   │ │(子包)   │  │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘  │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────┴──────────────────────────────┐   │
│  │  前端基础设施                                         │   │
│  │  ├── WXML/WXSS/JS (ES2020)                           │   │
│  │  ├── ECharts-for-Weixin (趋势图)                     │   │
│  │  ├── MobX-like 自研响应式Store                        │   │
│  │  ├── wx.request / wx.uploadFile                      │   │
│  │  └── wx.connectSocket (WebSocket)                    │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
         HTTPS (REST)              WSS (WebSocket)
         功能请求                  AI流式对话/实时推送
              │                         │
┌─────────────┴─────────────────────────┴─────────────────────┐
│                    后端服务层 (Python/FastAPI)               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              API Gateway 层                          │   │
│  │  ├── FastAPI HTTP Router (REST API)                 │   │
│  │  ├── WebSocket Manager (连接池/心跳/广播)            │   │
│  │  ├── JWT Auth Middleware (python-jose)              │   │
│  │  ├── Rate Limiter (slowapi)                         │   │
│  │  └── Request Logger (loguru)                        │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │              Service 业务逻辑层                       │   │
│  │  ├── MemberService          (成员/家庭管理)          │   │
│  │  ├── IndicatorService       (指标CRUD/异常判断)       │   │
│  │  ├── ReportService          (报告/OCR/AI解读)        │   │
│  │  ├── HospitalService        (住院/盯盘/对比)         │   │
│  │  ├── AIService              (对话/上下文/推送)        │   │
│  │  ├── ReminderService        (提醒触发/日历)          │   │
│  │  ├── ChildService           (疫苗/成长/里程碑)       │   │
│  │  └── ExportService          (Excel/PDF导出)          │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │              AI Provider 抽象层                      │   │
│  │  ├── AIProvider (ABC抽象接口)                        │   │
│  │  ├── KimiProvider / DeepSeekProvider                │   │
│  │  ├── OpenAIProvider / QwenProvider                  │   │
│  │  └── ProviderFactory (配置化创建+故障降级)           │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │              Repository 数据访问层                    │   │
│  │  ├── MySQL 8.0 (SQLAlchemy 2.0 async ORM)           │   │
│  │  ├── Redis 7.x (aioredis)                           │   │
│  │  └── MinIO / 阿里云OSS (图片对象存储)                 │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │              Celery Worker 异步任务层                 │   │
│  │  ├── OCR 异步识别任务                                │   │
│  │  ├── 报告 AI 解读任务                                │   │
│  │  └── 定时提醒推送任务                                │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
    ┌─────────┐      ┌─────────┐      ┌─────────┐
    │ MySQL   │      │ Redis   │      │  OSS    │
    │ (主库)   │      │(缓存/会话)│     │(图片存储) │
    └─────────┘      └─────────┘      └─────────┘
```

### 1.2 通信协议分工

| 协议 | 用途 | 特点 | 典型场景 |
|------|------|------|---------|
| **HTTP/1.1 REST API** | 所有功能型请求 | 无状态、可缓存、易调试 | 成员CRUD、指标查询、报告上传、时间轴分页 |
| **WebSocket** | AI对话流式传输 + 实时推送 | 长连接、双向流、低延迟 | AI打字机效果、异常实时预警、住院日报推送 |

### 1.3 技术选型理由

| 技术项 | 选型 | 核心理由 |
|--------|------|---------|
| 前端框架 | 原生微信小程序 | 用户明确要求原生SDK，性能最优，无跨端兼容层开销 |
| 后端语言 | Python 3.11+ | AI生态最强，Prompt工程与数据处理效率最高 |
| Web框架 | FastAPI | 原生异步支持WebSocket，自动OpenAPI文档，类型安全 |
| 数据库 | MySQL 8.0 | 关系型数据强一致性，事务完善，运维成熟 |
| ORM | SQLAlchemy 2.0 | Python异步ORM标准，类型提示完善 |
| 缓存 | Redis 7.x | 会话、热点数据、WebSocket连接映射、限流计数 |
| 任务队列 | Celery + Redis | Python生态成熟，与FastAPI配合顺畅 |
| 对象存储 | MinIO / 阿里云OSS | 私有化部署选MinIO，生产环境选OSS+CDN |
| 图表 | ECharts-for-Weixin | 微信小程序官方适配，Canvas绘制，支持参考线/缩放 |

### 1.4 配套文档索引

本文档为**高阶架构概览**，具体实现细节请查阅以下专项文档：

| 文档 | 内容 | 读者 |
|------|------|------|
| [`api_protocol.md`](./api_protocol.md) | HTTP REST 接口、WebSocket 消息协议、错误码、限流规则 | 前后端开发 |
| [`data_model.md`](./data_model.md) | ER 图、SQL DDL、索引策略、字段约束、JSON 字段约定 | 后端开发 / DBA |
| [`frontend_design.md`](./frontend_design.md) | 项目结构、分包策略、组件封装、Store、API 封装、WebSocket 客户端、离线处理 | 前端开发 |
| [`backend_design.md`](./backend_design.md) | 项目结构、FastAPI 配置、依赖注入、Service 实现、AI Provider、Celery 任务、异常引擎 | 后端开发 |

---

## 二、前端架构设计

### 2.1 项目结构与分包策略

前端采用**原生微信小程序**开发，主包体积限制 2MB，通过分包加载控制体积：

| 分包名称 | 包含页面 | 预估体积 | 触发加载 |
|---------|---------|---------|---------|
| `member` | 成员详情、指标中心、报告详情、趋势图 | ~800KB | 点击成员卡片时预加载 |
| `hospital` | 住院总览、盯盘、对比、批次 | ~600KB | 点击住院节点时加载 |
| `child` | 儿童看板、疫苗、成长曲线、里程碑 | ~700KB | 点击儿童卡片时预加载 |

**5Tab 导航架构**：首页 / 指标 / AI / 上传 / 我的

详细项目结构、app.json 配置、各工具类实现见 [`frontend_design.md`](frontend_design.md)。

### 2.2 前端核心能力

| 能力 | 方案 | 说明 |
|------|------|------|
| 状态管理 | 自研 Proxy-based Store (~200行) | 轻量级，无需引入 Redux/MobX |
| HTTP 请求 | `wx.request` 封装 | 自动 JWT 续期、401 静默刷新 |
| WebSocket | `wx.connectSocket` 封装 | 自动重连（指数退避）、心跳保活、消息路由 |
| 图表 | ECharts-for-Weixin | 趋势图含正常范围背景带、参考虚线 |
| 浮层交互 | 自研 Bottom Sheet 组件 | 统一趋势图/AI/异常三种浮层，支持下滑关闭 |
| 离线处理 | 本地 Storage 缓存 + 上传队列 | 弱网拍照缓存，联网后自动 flush |
| 订阅消息 | `wx.requestSubscribeMessage` | 引导用户授权，未授权 fallback 到 WebSocket |

### 2.3 家庭成员共享前端流程

```
创建者流程：
我的页 → 邀请家人 → 调用 wx.shareAppMessage
    ↓
分享卡片：{"title": "邀请你加入张家", "path": "/pages/join/index?token=xxx"}
    ↓
被邀请人点击卡片 → 进入 pages/join/index
    ↓
join页面逻辑：
  1. 解析 token 参数
  2. 调用 wx.login 获取 code
  3. POST /api/members/join {token, code}
  4. 后端返回：{member, family, jwt_token}
  5. 前端自动保存 token 到 storage
  6. 弹出关系选择：["爸爸", "妈妈", "孩子", "其他"]
  7. PUT /api/members/me {relation}
  8. 自动跳转到首页，显示所有家庭成员
```

---

## 三、后端架构设计

### 3.1 分层架构

后端采用**四层架构**：API Gateway → Service → AI Provider → Repository。

| 层级 | 职责 | 关键组件 |
|------|------|---------|
| **API Gateway** | 路由、认证、限流、日志 | FastAPI Router、JWT Middleware、Rate Limiter |
| **Service** | 业务逻辑、数据编排 | MemberService、IndicatorService、ReportService 等 |
| **AI Provider** | 多模型抽象、故障降级 | AIProvider ABC、ProviderFactory、Fallback 链 |
| **Repository** | 数据持久化、缓存、对象存储 | SQLAlchemy 2.0 async ORM、aioredis、OSS SDK |

### 3.2 异步任务层（Celery）

耗时操作通过 Celery Worker 异步执行，避免阻塞 HTTP 请求：

| 任务 | 触发方式 | 说明 |
|------|---------|------|
| OCR 识别 | 报告上传后提交 | 调用 AI 多模态解析图片，提取结构化指标 |
| 报告 AI 解读 | OCR 完成后链式触发 | 生成自然语言摘要 |
| 定时提醒推送 | Celery Beat 定时触发 | 每日 8:00 推送待办摘要，每小时检查逾期提醒 |
| 数据自动清理 | Celery Beat 定时触发 | 每日凌晨 3:00 清理过期 AI 对话、软删除成员、临时文件 |

### 3.3 后端核心能力

| 能力 | 方案 | 说明 |
|------|------|------|
| 认证鉴权 | JWT (python-jose) + 微信 code2session | Token 有效期 30 天，支持静默刷新 |
| 依赖注入 | FastAPI `Depends` | DB Session、Redis、当前用户统一注入 |
| WebSocket 管理 | 自研 ConnectionManager | member_id → websocket[] 映射，支持多设备同时在线 |
| 限流 | slowapi | IP 级限流，AI 对话 30/分钟，上传 20/分钟 |
| 事务一致性 | SQLAlchemy `async_session.begin()` | OCR 完成后 reports + indicator_data + health_events 三表原子写入 |

详细项目结构、Service 实现、AI Provider 代码、Celery 任务代码见 [`backend_design.md`](backend_design.md)。

---

## 四、关键模块设计

### 4.1 AI Provider 抽象层

设计目标：支持多模型提供商（Kimi/DeepSeek/OpenAI/通义千问）无缝切换，单点故障自动降级。

**核心接口**：
- `chat(messages, stream)` — 通用对话
- `analyze_image(image_url, prompt)` — 图片 OCR/指标提取
- `generate_summary(context)` — 生成就诊摘要

**故障降级策略**：默认 Provider 失败时，按预设优先级依次尝试备用 Provider，全部失败时返回 503 错误。

详细 Provider 实现代码见 [`backend_design.md`](backend_design.md) 第 6 节。

### 4.2 OCR 与报告解析流水线

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
    3. Prompt 工程提取结构化指标
    4. 指标标准化映射（名称/单位归一化）
    5. 异常判断引擎计算状态
    6. 数据库事务写入（reports + indicator_data + health_events）
    7. WebSocket推送 "ocr_complete" 给前端
    ↓
前端收到推送 → 自动刷新 → 显示结果页
```

**关键设计点**：
- 客户端压缩质量 ≥0.9，确保 OCR 准确率
- 服务端生成缩略图用于展示，原图仅用于 OCR
- 三表写入包裹在数据库事务中，失败自动回滚并标记报告 `ocr_status=failed`
- 重试 3 次后进入失败终态，前端引导重新拍照或手动输入

详细 OCR Task 实现见 [`backend_design.md`](backend_design.md) 第 7 节。

### 4.3 异常判断引擎

后端返回 4 级状态（`normal`/`low`/`high`/`critical`），前端映射为 3 色体系：

| 后端状态 | 前端颜色 | 前端文案 |
|---------|---------|---------|
| `normal` | 正常 | 正常 |
| `low` | 注意 | 偏低 |
| `high` | 注意 | 偏高 |
| `critical` | 严重异常 | 严重异常 |

**引擎能力**：
- 指标名称标准化（同义词库 + Levenshtein 距离）
- 年龄段自适应阈值（儿童/成人/老人）
- 危急值自动判定（偏离参考范围 30% 以上）
- 偏离百分比计算（用于后端自动判断提醒紧急程度）
- 趋势评价（结合指标特性判断变化好坏）

详细引擎实现见 [`backend_design.md`](backend_design.md) 第 8 节。

### 4.4 AI 对话上下文管理

采用**四级上下文**构建策略，确保 AI 回答精准且个性化：

1. **成员信息**：姓名、年龄、性别、血型、过敏史
2. **页面场景**：当前所在页面（如指标详情页、住院总览页）
3. **当前指标**：如果是指标页，注入最近 5 次历史记录
4. **最近异常**：最近 30 天所有异常指标列表

**对话持久化**：最近 10 轮对话保存到 `ai_conversations` 表，按 `page_context` 隔离不同场景的对话历史。

详细 AI Service 实现见 [`backend_design.md`](backend_design.md) 第 9 节。

### 4.5 提醒系统

**提醒来源**：
- 系统规则自动生成（疫苗到期前 14 天、复查前 7 天）
- 异常指标触发（前端选择"观察"→7 天后复查；前端选择"去看看"→后端根据偏离程度自动判断 1~3 天）

**推送通道优先级**：
1. 微信小程序订阅消息（仅当用户已授权该模板）
2. WebSocket 实时推送（在线用户，无论是否订阅）
3. Redis 待办横幅（未订阅用户，下次打开小程序时首页展示）

详细 ReminderService 实现见 [`backend_design.md`](backend_design.md) 第 10 节。

### 4.6 数据导出

支持两种导出格式：
- **Excel**：指标历史数据，状态列颜色标记（正常=绿色、注意=黄色、严重=红色）
- **PDF 就诊摘要**：调用 AI 生成 Markdown 摘要，再渲染为 PDF（需嵌入中文字体）

另支持 GDPR/个保法合规的**完整个人数据导出**（JSON 格式，含全部指标、报告、事件、对话记录）。

---

## 五、数据库设计概览

### 5.1 ER 关系图

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   family    │ 1     │   member    │ 1     │ indicator   │
│  (家庭)      │◄─────►│  (成员)      │◄─────►│  (指标数据)  │
└─────────────┘       └──────┬──────┘       └─────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   report    │      │  hospital   │      │ health_event│
│  (报告)      │      │  (住院事件)  │      │  (健康事件)  │
└─────────────┘      └─────────────┘      └─────────────┘

┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   reminder  │      │ai_conversat.│      │   vaccine   │
│  (提醒)      │      │  (AI对话)    │      │  (疫苗记录)  │
└─────────────┘      └─────────────┘      └─────────────┘
```

### 5.2 核心数据表

| 表名 | 用途 | 数据量预估 |
|------|------|-----------|
| `families` | 家庭基础信息 | 小 |
| `members` | 成员档案（含微信订阅状态） | 中 |
| `indicator_data` | 指标测量记录（数据量最大） | 大 |
| `reports` | 报告元数据 + AI 提取结果 | 中 |
| `hospital_events` | 住院事件 + 关键节点 | 小 |
| `health_events` | 统一时间轴事件 | 中 |
| `reminders` | 提醒任务 | 中 |
| `ai_conversations` | AI 对话历史 | 中 |
| `vaccine_records` | 疫苗接种记录 | 小 |

### 5.3 关键设计决策

- 主键统一使用 `VARCHAR(36)` UUID，程序生成
- 数值统一使用 `DECIMAL(10,3)`，百分比使用 `DECIMAL(5,2)`
- JSON 字段用于 allergies、chronic_diseases、images、messages 等半结构化数据
- 所有外键使用 `ON DELETE CASCADE` 实现级联删除
- `indicator_data` 为最高频查询表，建立 `(member_id, indicator_key, record_date)` 复合索引

详细的 SQL DDL、索引策略、字段约束见 [`data_model.md`](data_model.md)。

---

## 六、部署与运维

### 6.1 Docker Compose 本地部署

提供完整的 `docker-compose.yml` 用于本地开发环境一键启动：
- `api` 服务：FastAPI 应用
- `celery-worker`：异步任务执行
- `celery-beat`：定时任务调度
- `mysql`：MySQL 8.0 主库
- `redis`：Redis 7.x 缓存/消息队列
- `minio`：对象存储（私有化替代方案）

详细 `docker-compose.yml` 配置见 [`backend_design.md`](backend_design.md) 项目结构章节。

### 6.2 生产环境架构

```
                    ┌─────────────┐
                    │   CDN       │
                    │ (图片加速)   │
                    └──────┬──────┘
                           │
    ┌─────────────┐       │        ┌─────────────┐
    │  微信小程序  │◄──────┴───────►│  Nginx      │
    │  用户端      │   HTTPS/WSS    │ (反向代理)   │
    └─────────────┘                └──────┬──────┘
                                          │
                         ┌────────────────┼────────────────┐
                         ▼                ▼                ▼
                   ┌──────────┐    ┌──────────┐    ┌──────────┐
                   │FastAPI   │    │FastAPI   │    │FastAPI   │
                   │Instance 1│    │Instance 2│    │Instance 3│
                   └────┬─────┘    └────┬─────┘    └────┬─────┘
                        └────────────────┼────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
              ┌──────────┐       ┌──────────┐       ┌──────────┐
              │  MySQL   │       │  Redis   │       │  OSS     │
              │ 主从集群  │       │ Sentinel │       │ 私有Bucket│
              └──────────┘       └──────────┘       └──────────┘
```

**生产环境要点**：
- Nginx 反向代理 + TLS 1.3 终止
- FastAPI 多实例水平扩展（无状态设计）
- MySQL 主从集群，读写分离
- Redis Sentinel 高可用
- CDN 加速图片分发
- OSS 私有 Bucket + 预签名 URL（有效期 7 天）

### 6.3 监控与日志

| 层面 | 工具 | 监控项 |
|------|------|--------|
| 应用日志 | Loguru + FileBeat + ELK | 请求日志、错误日志、AI调用日志 |
| 性能指标 | Prometheus + Grafana | API响应时间、QPS、错误率、AI延迟 |
| 告警 | AlertManager | P99延迟>2s、错误率>1%、AI服务不可用 |
| 小程序 | 微信小程序性能监控 | 启动耗时、JS错误、接口成功率 |

---

## 七、安全方案

### 7.1 认证与鉴权

- **微信小程序登录**：`wx.login` 获取 code → 后端调用微信 `code2session` 获取 `openid` → 签发 JWT
- **JWT 有效期**：Access Token 30 天，支持静默刷新
- **数据权限**：所有查询强制带 `family_id` 过滤，禁止跨家庭数据访问
- **角色权限**：`creator`（完全控制）、`member`+`full`（读写）、`member`+`view`（只读）、`summary`（仅摘要）

### 7.2 数据安全分层

| 层级 | 措施 | 实现 |
|------|------|------|
| 传输层 | TLS 1.3 | Nginx 强制 HTTPS，HSTS头 |
| 存储层 | 字段级加密 | MySQL敏感字段（手机号、身份证号）AES-256加密 |
| 图片层 | 签名URL | OSS私有Bucket，后端生成7天过期预签名URL |
| 访问层 | 家庭隔离 | 所有查询强制带 family_id 过滤 |
| 审计层 | 操作日志 | `audit_logs` 表记录所有数据变更 |

### 7.3 防攻击措施

| 措施 | 规则 |
|------|------|
| IP 级限流 | 成员列表 100/分钟，AI 对话 30/分钟，上传 20/分钟，登录 10/分钟 |
| CORS | 仅允许 `https://servicewechat.com` |
| AI 调用熔断 | Provider 连续失败 3 次后自动切换，全部失败返回 503 |

### 7.4 合规清单

| 要求 | 实现 |
|------|------|
| 医疗免责声明 | 首页底部 + 每次AI回答末尾自动附加 |
| 隐私协议 | 首次使用弹窗强制同意，存储同意记录 |
| 数据删除 | `DELETE /api/members/me` 发起删除，30天后物理清除 |
| 数据导出 | `GET /api/export/all` 导出全部个人数据（JSON/Excel） |
| 儿童隐私 | 16岁以下数据额外加密，分享需创建者确认 |
| 等保合规 | 云服务商通过等保三级，应用层做好访问控制 |

### 7.5 AI 图像处理与数据隐私

**风险识别**：用户医疗报告原图含敏感个人信息，通过 URL 发送至第三方 AI 进行 OCR 解析。

**缓解措施**：

| 层级 | 措施 |
|------|------|
| 提供商选择 | 优先国内 Provider（Kimi/DeepSeek/通义千问），OpenAI 仅作为降级选项且需用户单独同意 |
| 图像预处理 | OCR 前可选脱敏（OpenCV 模糊姓名/身份证号区域） |
| 传输安全 | 发送至 AI 的图片 URL 有效期 ≤1 小时，OSS Bucket Policy 限制仅对应 Provider IP 段可访问 |
| 告知义务 | 首次上传时弹窗告知，用户点击"知道了"视为授权 |
| 数据删除 | Prompt 中明确要求"处理完成后立即删除图片，不得用于模型训练" |
| 审计追踪 | 记录每次 AI 图像调用的 provider、timestamp、report_id，保留 90 天 |

---

## 八、测试策略

### 8.1 测试分层

| 层级 | 工具 | 目标覆盖率 | 核心场景 |
|------|------|-----------|---------|
| 单元测试 | pytest + pytest-asyncio | >= 80% | Service层业务逻辑、异常判断算法、趋势计算 |
| 集成测试 | pytest + TestClient | >= 60% | API路由、数据库事务、Redis缓存一致性 |
| E2E测试 | Minium（微信官方） | 核心路径 | 上传→OCR→查看→设置提醒 完整闭环 |
| AI回归测试 | 自定义脚本 | 100%黄金集 | Prompt版本化 + 固定测试图片集 OCR准确率监控 |
| 性能测试 | locust | 关键指标 | 首页加载<2s、AI对话响应<5s、并发100用户 |

### 8.2 核心算法边界测试

异常判断引擎必须覆盖以下边界（参数化测试）：
- 范围内正常 / 低于下限 1 单位 / 高于上限 1 单位
- 恰好等于下限/上限（边界闭合）
- 低于下限 30%（危急值）/ 高于上限 30%（危急值）

### 8.3 AI Prompt 回归测试

建立黄金数据集（固定测试图片集），每张图定义期望识别的指标列表。CI 中运行 OCR 准确率测试，若低于 80% 阈值则阻止部署。

### 8.4 前端核心路径 E2E

使用 Minium 框架覆盖：上传报告 → OCR 识别 → 查看结果 → 设置提醒 的完整用户闭环。

详细测试代码示例见 [`backend_design.md`](backend_design.md) 第 8 节和 [`frontend_design.md`](frontend_design.md) 相关章节。

---

## 九、数据生命周期管理

### 9.1 数据保留策略

| 数据类型 | 保留期限 | 删除方式 | 说明 |
|----------|----------|----------|------|
| 报告原图 | 账号注销后1年 | 物理删除 | 满足医疗记录保存要求 |
| 指标数据 | 账号注销后1年 | 物理删除 | 核心健康数据 |
| AI对话记录 | 90天 | 自动清理 | 定期清理任务 |
| 操作审计日志 | 1年 | 自动清理 | 合规要求 |
| AI调用日志 | 90天 | 自动清理 | 含provider/timestamp，不含图片URL |
| 已删除成员数据 | 软删除后1年 | 物理删除 | 先标记deleted_at，1年后清理 |
| 微信订阅状态 | 随账号生命周期 | 账号注销时删除 | — |
| 导出文件临时副本 | 24小时 | 自动清理 | 导出任务完成后保留24小时供下载 |

### 9.2 自动清理任务

每日凌晨 3:00 由 Celery Beat 触发 `cleanup_expired_data` 任务：
- 清理 90 天前的 AI 对话记录
- 清理 1 年前的软删除成员数据
- 清理 24 小时前的导出临时文件

详细清理任务实现见 [`backend_design.md`](backend_design.md) 第 13 节。

---

> 本文档为家庭智能健康助手的高阶架构概览。具体实现细节请参阅配套专项文档：
> - [`api_protocol.md`](api_protocol.md) — 接口协议
> - [`data_model.md`](data_model.md) — 数据模型
> - [`frontend_design.md`](frontend_design.md) — 前端项目设计
> - [`backend_design.md`](backend_design.md) — 后端项目设计
