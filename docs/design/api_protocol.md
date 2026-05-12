# 家庭智能健康助手 — 接口协议文档

> 版本：v1.0 | 日期：2026-05-08 | 读者：前后端开发工程师 | 状态：设计定稿

---

## 目录

1. [通用约定](#一通用约定)
2. [认证与授权](#二认证与授权)
3. [REST API 接口](#三rest-api-接口)
4. [WebSocket 消息协议](#四websocket-消息协议)
5. [错误码定义](#五错误码定义)
6. [限流规则](#六限流规则)

---

## 一、通用约定

### 1.1 基础信息

| 项目 | 值 |
|------|-----|
| 基础URL | `https://api.health-helper.example.com` |
| 协议 | HTTPS 1.1 / WSS |
| 数据格式 | JSON |
| 字符编码 | UTF-8 |
| 时间格式 | ISO 8601 (`2026-05-08T14:30:00+08:00`) |
| 日期格式 | `YYYY-MM-DD` |

### 1.2 请求规范

- 所有请求需在 Header 中携带 `Authorization: Bearer <jwt_token>`
- Content-Type: `application/json`（上传文件除外）
- 请求体中布尔值使用 JSON 原生 `true`/`false`

### 1.3 响应规范

所有成功响应返回 HTTP 200，结构如下：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

列表分页响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [ ... ],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "has_more": true
  }
}
```

---

## 二、认证与授权

### 2.1 微信小程序登录

```
POST /api/auth/login
```

**请求体**：

```json
{
  "code": "wx_login_code_xxx"  // 微信小程序 wx.login() 获取的临时 code
}
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 2592000,
    "member": {
      "id": "m_xxx",
      "name": "张三",
      "family_id": "f_xxx",
      "role": "admin"
    }
  }
}
```

### 2.2 Token 刷新

```
POST /api/auth/refresh
```

**请求体**：

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

### 2.3 WebSocket 连接认证

WebSocket 连接时通过 `Sec-WebSocket-Protocol` header 传递 token，避免 URL 中泄露 JWT：

```
wss://api.health-helper.example.com/ws
Headers:
  Sec-WebSocket-Protocol: health-protocol, <jwt_token>
```

> 微信小程序 `wx.connectSocket` 支持 `protocols` 数组参数传递 token。

---

## 三、REST API 接口

### 3.1 成员管理 (`/api/members`)

#### 获取当前成员信息

```
GET /api/members/me
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "id": "m_xxx",
    "name": "张三",
    "avatar_url": "https://...",
    "birth_date": "1985-03-15",
    "gender": "male",
    "blood_type": "A",
    "allergies": ["青霉素"],
    "chronic_diseases": ["高血压"],
    "type": "adult",
    "role": "creator",
    "subscription_status": {
      "daily_digest": true,
      "urgent_alert": true,
      "review_reminder": false
    }
  }
}
```

#### 更新当前成员信息

```
PUT /api/members/me
```

**请求体**：

```json
{
  "name": "张三",
  "birth_date": "1985-03-15",
  "gender": "male",
  "blood_type": "A",
  "allergies": ["青霉素", "花生"],
  "chronic_diseases": ["高血压"],
  "type": "adult"
}
```

#### 更新微信订阅状态

```
PUT /api/members/me/subscription
```

**请求体**：

```json
{
  "daily_digest": true,
  "urgent_alert": false
}
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "subscription_status": {
      "daily_digest": true,
      "urgent_alert": false
    }
  }
}
```

#### 获取家庭成员列表

```
GET /api/members
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "family": {
      "id": "f_xxx",
      "name": "张三的家庭",
      "creator_id": "m_xxx",
      "invite_code": "ABC123"
    },
    "members": [
      {
        "id": "m_xxx",
        "name": "张三",
        "avatar_url": "https://...",
        "type": "adult",
        "role": "admin"
      },
      {
        "id": "m_yyy",
        "name": "李四",
        "type": "child",
        "role": "member"
      }
    ]
  }
}
```

#### 创建家庭

```
POST /api/members/family
```

**请求体**：

```json
{
  "creator_name": "张三",
  "creator_info": {
    "birth_date": "1985-03-15",
    "gender": "male"
  }
}
```

#### 生成邀请链接

```
POST /api/members/invite
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "invite_link": "https://api.health-helper.example.com/join?token=xxx",
    "expires_at": "2026-05-15T08:00:00+08:00"
  }
}
```

#### 通过链接加入家庭

```
POST /api/members/join
```

**请求体**：

```json
{
  "token": "invite_jwt_token",
  "code": "wx_login_code"
}
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "member": { "id": "m_zzz", "name": "王五", ... },
    "family": { "id": "f_xxx", "name": "张三的家庭" },
    "jwt_token": "eyJhbGciOiJIUzI1NiIs..."
  }
}
```

#### 删除成员（危险操作）

```
DELETE /api/members/{member_id}
```

**说明**：仅家庭创建者可删除其他成员。删除成员会级联删除该成员的全部指标、报告、事件等数据。

---

### 3.2 指标管理 (`/api/indicators`)

#### 获取成员指标列表

```
GET /api/indicators?member_id={member_id}&page=1&page_size=20
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "i_xxx",
        "indicator_key": "systolic_bp",
        "indicator_name": "收缩压",
        "value": 135.0,
        "unit": "mmHg",
        "lower_limit": 90.0,
        "upper_limit": 140.0,
        "status": "normal",
        "deviation_percent": 0.00,
        "record_date": "2026-05-08",
        "record_time": "09:30:00"
      }
    ],
    "total": 50,
    "page": 1,
    "page_size": 20,
    "has_more": true
  }
}
```

#### 获取单个指标历史

```
GET /api/indicators/{indicator_key}/history?member_id={member_id}&limit=30
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "indicator_key": "systolic_bp",
    "indicator_name": "收缩压",
    "unit": "mmHg",
    "lower_limit": 90.0,
    "upper_limit": 140.0,
    "history": [
      { "date": "2026-05-08", "value": 135.0, "status": "normal" },
      { "date": "2026-05-01", "value": 142.0, "status": "high" }
    ],
    "trend": {
      "direction": "down",
      "magnitude": "small",
      "evaluation": "improving"
    }
  }
}
```

#### 获取最近异常指标

```
GET /api/indicators/abnormal?member_id={member_id}&days=30
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "total": 3,
    "items": [
      {
        "indicator_key": "fasting_glucose",
        "indicator_name": "空腹血糖",
        "value": 7.2,
        "unit": "mmol/L",
        "status": "high",
        "deviation_percent": 20.00,
        "record_date": "2026-05-08",
        "suggested_action": "观察"
      }
    ]
  }
}
```

#### 手动录入指标

```
POST /api/indicators
```

**请求体**：

```json
{
  "member_id": "m_xxx",
  "indicator_key": "systolic_bp",
  "indicator_name": "收缩压",
  "value": 135.0,
  "unit": "mmHg",
  "lower_limit": 90.0,
  "upper_limit": 140.0,
  "record_date": "2026-05-08",
  "record_time": "09:30:00"
}
```

---

### 3.3 报告管理 (`/api/reports`)

#### 上传报告图片

```
POST /api/reports/upload
Content-Type: multipart/form-data
```

**请求参数**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `member_id` | string | 成员ID |
| `file` | file | 报告图片文件 |
| `type` | string | 报告类型：`lab`/`diagnosis`/`prescription`/`discharge` |
| `hospital` | string | 医院名称（可选） |
| `department` | string | 科室（可选） |
| `report_date` | date | 报告日期（可选，默认今天） |

**响应**：

```json
{
  "code": 0,
  "data": {
    "report_id": "r_xxx",
    "image_url": "https://oss.example.com/reports/xxx.jpg",
    "ocr_status": "pending",
    "message": "AI正在读报告，请稍候..."
  }
}
```

#### 获取报告列表

```
GET /api/reports?member_id={member_id}&page=1&page_size=10
```

#### 获取报告详情

```
GET /api/reports/{report_id}
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "id": "r_xxx",
    "type": "lab",
    "hospital": "协和医院",
    "department": "检验科",
    "report_date": "2026-05-08",
    "images": ["https://oss.example.com/reports/xxx.jpg"],
    "extracted_indicators": [
      {
        "indicator_key": "hemoglobin",
        "indicator_name": "血红蛋白",
        "value": 125.0,
        "unit": "g/L",
        "status": "normal",
        "deviation_percent": 0.00
      }
    ],
    "ai_summary": "本次血常规检查整体正常...",
    "ocr_status": "completed",
    "created_at": "2026-05-08T10:00:00+08:00"
  }
}
```

---

### 3.4 住院管理 (`/api/hospitals`)

#### 创建住院事件

```
POST /api/hospitals
```

**请求体**：

```json
{
  "member_id": "m_xxx",
  "hospital": "协和医院",
  "department": "心内科",
  "admission_date": "2026-05-01",
  "diagnosis": "冠心病",
  "doctor": "李医生",
  "watch_indicators": ["systolic_bp", "fasting_glucose"]
}
```

#### 获取住院列表

```
GET /api/hospitals?member_id={member_id}
```

#### 获取住院详情（含今日vs昨日对比）

```
GET /api/hospitals/{hospital_id}/comparison
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "hospital_id": "h_xxx",
    "today": "2026-05-08",
    "yesterday": "2026-05-07",
    "total": 5,
    "improved": 2,
    "worsened": 1,
    "stable": 2,
    "indicators": [
      {
        "indicator_key": "systolic_bp",
        "indicator_name": "收缩压",
        "today": 135.0,
        "yesterday": 142.0,
        "change": -7.0,
        "change_percent": -4.9,
        "evaluation": "improving",
        "unit": "mmHg"
      }
    ]
  }
}
```

#### 出院

```
PUT /api/hospitals/{hospital_id}/discharge
```

**请求体**：

```json
{
  "discharge_date": "2026-05-10",
  "summary": "病情稳定，准予出院"
}
```

---

### 3.5 AI 对话 (`/api/ai`)

#### 发送消息（非流式）

```
POST /api/ai/chat
```

**请求体**：

```json
{
  "member_id": "m_xxx",
  "message": "我的血压最近怎么样？",
  "page_context": "indicator:systolic_bp"
}
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "reply": "您最近30天的收缩压整体在正常范围内...",
    "data_cards": [
      {
        "type": "indicator",
        "title": "收缩压趋势",
        "value": "135 mmHg",
        "status": "normal",
        "trend": "improving"
      }
    ],
    "suggested_questions": ["需要调整用药吗？", "饮食有什么建议？"]
  }
}
```

**说明**：流式对话通过 WebSocket 进行，见第 4 节。

#### 获取对话历史

```
GET /api/ai/conversations?member_id={member_id}&page_context={page_context}
```

---

### 3.6 提醒管理 (`/api/reminders`)

#### 获取提醒列表

```
GET /api/reminders?member_id={member_id}&status=pending&page=1
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "rem_xxx",
        "type": "review",
        "title": "空腹血糖复查提醒",
        "description": "建议1周后复查空腹血糖",
        "scheduled_date": "2026-05-15",
        "status": "pending",
        "priority": "high",
        "related_indicator": "空腹血糖"
      }
    ],
    "total": 5
  }
}
```

#### 创建提醒

```
POST /api/reminders
```

**请求体**：

```json
{
  "member_id": "m_xxx",
  "type": "review",
  "title": "复查提醒",
  "description": "建议复查",
  "scheduled_date": "2026-05-15",
  "priority": "high",
  "related_indicator": "空腹血糖"
}
```

#### 完成提醒

```
PUT /api/reminders/{reminder_id}/complete
```

#### 获取每日待办

```
GET /api/reminders/daily-digest?member_id={member_id}
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "date": "2026-05-08",
    "total": 3,
    "critical_count": 1,
    "items": [ ... ],
    "summary": "今天有1项紧急提醒和2项普通提醒"
  }
}
```

---

### 3.7 儿童管理 (`/api/child`)

#### 获取儿童看板

```
GET /api/child/dashboard?member_id={member_id}
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "member_id": "m_xxx",
    "age_months": 18,
    "age_display": "1岁6个月",
    "todos": [
      { "type": "vaccine", "title": "麻腮风疫苗第2针", "status": "upcoming", "scheduled_date": "2026-05-15" }
    ],
    "positives": [
      { "type": "growth", "title": "身高增长正常", "detail": "本月增长2cm" }
    ],
    "quick_links": ["growth", "vaccine", "milestone", "ai"],
    "ai_suggestions": ["辅食怎么吃？", "缺钙的表现？", "出牙要注意什么？"]
  }
}
```

#### 获取疫苗记录

```
GET /api/child/vaccines?member_id={member_id}&status=all
```

#### 更新疫苗记录

```
PUT /api/child/vaccines/{vaccine_id}
```

**请求体**：

```json
{
  "actual_date": "2026-05-08",
  "status": "completed",
  "location": "社区医院",
  "batch_no": "20260401A",
  "reaction": "无不良反应"
}
```

---

### 3.8 数据导出 (`/api/export`)

#### 导出 Excel

```
GET /api/export/excel?member_id={member_id}&start_date=2026-01-01&end_date=2026-05-08
```

**响应**：文件下载（`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`）

#### 导出就诊摘要 PDF

```
GET /api/export/summary?member_id={member_id}&hospital_id={hospital_id}
```

**响应**：文件下载（`application/pdf`）

#### 导出全部个人数据（GDPR/个保法合规）

```
GET /api/export/all
```

**响应**：JSON 格式的完整个人数据导出。

---

## 四、WebSocket 消息协议

### 4.1 连接与心跳

**连接URL**：

```
wss://api.health-helper.example.com/ws
```

**认证方式**：通过 `Sec-WebSocket-Protocol` header 传递 JWT（详见 2.3 节）。

**心跳机制**：

客户端每 30 秒发送一次 ping：

```json
{ "type": "ping" }
```

服务端响应 pong：

```json
{ "type": "pong" }
```

### 4.2 AI 流式对话

**客户端发送消息**：

```json
{
  "type": "chat",
  "member_id": "m_xxx",
  "message": "我的血压最近怎么样？",
  "page_context": "indicator:systolic_bp"
}
```

**服务端流式响应**（逐字推送）：

```json
{ "type": "chat_chunk", "content": "您" }
{ "type": "chat_chunk", "content": "最近" }
{ "type": "chat_chunk", "content": "30天" }
...
{ "type": "chat_done", "content": "您最近30天的收缩压整体在正常范围内..." }
```

### 4.3 OCR 完成推送

当异步 OCR 任务完成后，服务端主动推送：

```json
{
  "type": "ocr_complete",
  "report_id": "r_xxx",
  "indicator_count": 12,
  "abnormal_count": 2
}
```

### 4.4 每日待办推送

每天早上 8:00 或用户首次连接时推送：

```json
{
  "type": "daily_digest",
  "payload": {
    "date": "2026-05-08",
    "total": 3,
    "critical_count": 1,
    "items": [ ... ],
    "summary": "今天有1项紧急提醒和2项普通提醒"
  }
}
```

### 4.5 成员加入通知

当新成员通过邀请链接加入家庭时，推送给创建者：

```json
{
  "type": "member_joined",
  "member_name": "王五"
}
```

---

## 五、错误码定义

### 5.1 全局错误码

| 错误码 | HTTP状态 | 说明 | 示例场景 |
|--------|---------|------|---------|
| `0` | 200 | 成功 | — |
| `1001` | 400 | 请求参数错误 | 必填字段缺失 |
| `1002` | 401 | 未授权 | Token 过期或无效 |
| `1003` | 403 | 无权访问 | 尝试访问非家庭成员数据 |
| `1004` | 404 | 资源不存在 | 成员/报告 ID 不存在 |
| `1005` | 409 | 资源冲突 | 重复创建家庭 |
| `1006` | 429 | 请求过于频繁 | 触发限流 |
| `1007` | 500 | 服务器内部错误 | 数据库连接失败 |
| `1008` | 503 | 服务暂不可用 | AI Provider 全部故障 |

### 5.2 业务错误码

| 错误码 | HTTP状态 | 说明 | 示例场景 |
|--------|---------|------|---------|
| `2001` | 400 | 邀请链接已过期 | join 时 token 过期 |
| `2002` | 400 | OCR 识别失败 | 图片模糊/非医疗报告 |
| `2003` | 400 | 指标值不合法 | 数值超出合理范围 |
| `2004` | 403 | 非创建者无法删除成员 | 普通成员尝试删除他人 |
| `2005` | 400 | 订阅消息未授权 | 用户拒绝订阅授权 |

### 5.3 错误响应格式

```json
{
  "code": 1002,
  "message": "Token 已过期，请重新登录",
  "data": null
}
```

---

## 六、限流规则

基于客户端 IP 地址限流（`slowapi` 实现）：

| 接口 | 限流规则 | 说明 |
|------|---------|------|
| `GET /api/members` | 100/分钟 | 成员列表查询 |
| `POST /api/ai/chat` | 30/分钟 | AI 对话（更严格） |
| `POST /api/reports/upload` | 20/分钟 | 报告上传 |
| `POST /api/auth/login` | 10/分钟 | 登录（防暴力破解） |
| `GET /api/indicators` | 200/分钟 | 指标查询（高频） |
| `GET /api/export/*` | 5/分钟 | 导出（资源消耗大） |

**限流响应**（HTTP 429）：

```json
{
  "code": 1006,
  "message": "请求过于频繁，请稍后再试",
  "data": {
    "retry_after": 30
  }
}
```
