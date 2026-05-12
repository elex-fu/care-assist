# 家庭智能健康助手 — 数据模型设计

> 版本：v1.0 | 日期：2026-05-08 | 读者：后端开发工程师 / DBA | 状态：设计定稿

---

## 目录

1. [ER 关系图](#一er-关系图)
2. [核心表结构](#二核心表结构)
3. [索引策略](#三索引策略)
4. [字段说明与约束](#四字段说明与约束)

---

## 一、ER 关系图

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

**关系说明**：
- `family` 1:N `member` — 一个家庭成员管理多个成员
- `member` 1:N `indicator_data` / `report` / `hospital_events` / `health_events` / `reminder` / `ai_conversations` / `vaccine_records`
- `report` → `indicator_data`（通过 `source_report_id` 关联）
- `hospital_events` → `indicator_data`（通过 `source_hospital_id` 关联）

---

## 二、核心表结构

### 2.1 家庭表 (`families`)

```sql
CREATE TABLE families (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL DEFAULT '我的家庭',
    admin_id VARCHAR(36),  -- 家庭管理员ID，拥有完整管理权限
    invite_code VARCHAR(10) UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_invite_code (invite_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2.2 成员表 (`members`)

```sql
CREATE TABLE members (
    id VARCHAR(36) PRIMARY KEY,
    family_id VARCHAR(36) NOT NULL,
    name VARCHAR(50) NOT NULL,
    avatar_url VARCHAR(500),
    birth_date DATE,
    gender ENUM('male', 'female') NOT NULL,
    blood_type ENUM('A','B','AB','O'),
    allergies JSON DEFAULT '[]',
    chronic_diseases JSON DEFAULT '[]',
    type ENUM('adult','child','elderly') DEFAULT 'adult',
    role ENUM('creator','member') DEFAULT 'member',
    -- 角色说明：creator = 家庭创建者/管理员（可编辑全部数据、邀请家人）；member = 家人（可查看全部、仅编辑自己数据）
    wx_openid VARCHAR(100),
    subscription_status JSON DEFAULT '{}',
    -- 示例：{"daily_digest": true, "urgent_alert": true, "review_reminder": false}
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
    INDEX idx_family (family_id),
    INDEX idx_wx_openid (wx_openid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2.3 指标数据点表 (`indicator_data`)

数据量最大的表，存储每一次指标测量记录。

```sql
CREATE TABLE indicator_data (
    id VARCHAR(36) PRIMARY KEY,
    member_id VARCHAR(36) NOT NULL,
    indicator_key VARCHAR(50) NOT NULL,        -- 标准化指标代码
    indicator_name VARCHAR(50) NOT NULL,       -- 显示名称
    value DECIMAL(10,3) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    lower_limit DECIMAL(10,3),
    upper_limit DECIMAL(10,3),
    status ENUM('normal','low','high','critical') NOT NULL,
    deviation_percent DECIMAL(5,2) DEFAULT 0.00,  -- 偏离参考范围的百分比（如 25.00 表示高25%）
    record_date DATE NOT NULL,
    record_time TIME,
    source_report_id VARCHAR(36),
    source_hospital_id VARCHAR(36),
    source_batch_id VARCHAR(36),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
    INDEX idx_member_date (member_id, record_date),
    INDEX idx_member_key_date (member_id, indicator_key, record_date),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2.4 报告表 (`reports`)

```sql
CREATE TABLE reports (
    id VARCHAR(36) PRIMARY KEY,
    member_id VARCHAR(36) NOT NULL,
    type ENUM('lab','diagnosis','prescription','discharge') NOT NULL,
    hospital VARCHAR(100),
    department VARCHAR(50),
    report_date DATE,
    images JSON NOT NULL,                      -- 图片URL数组
    extracted_indicators JSON,                 -- AI提取的原始指标
    ai_summary TEXT,
    hospital_id VARCHAR(36),
    ocr_status ENUM('pending','processing','completed','failed') DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
    INDEX idx_member_date (member_id, report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2.5 住院事件表 (`hospital_events`)

```sql
CREATE TABLE hospital_events (
    id VARCHAR(36) PRIMARY KEY,
    member_id VARCHAR(36) NOT NULL,
    hospital VARCHAR(100) NOT NULL,
    department VARCHAR(50),
    admission_date DATE NOT NULL,
    discharge_date DATE,
    diagnosis VARCHAR(200),
    doctor VARCHAR(50),
    key_nodes JSON DEFAULT '[]',
    watch_indicators JSON DEFAULT '[]',
    status ENUM('active','discharged') DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
    INDEX idx_member_status (member_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2.6 健康事件表 (`health_events`)

统一时间轴数据源。

```sql
CREATE TABLE health_events (
    id VARCHAR(36) PRIMARY KEY,
    member_id VARCHAR(36) NOT NULL,
    type ENUM('visit','lab','medication','symptom','ai','hospital','vaccine','checkup','milestone') NOT NULL,
    event_date DATE NOT NULL,
    event_time TIME,
    hospital VARCHAR(100),
    department VARCHAR(50),
    doctor VARCHAR(50),
    diagnosis TEXT,
    notes TEXT,
    report_id VARCHAR(36),
    hospital_id VARCHAR(36),
    status ENUM('normal','abnormal') DEFAULT 'normal',
    abnormal_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
    INDEX idx_member_date (member_id, event_date),
    INDEX idx_type (type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2.7 提醒表 (`reminders`)

```sql
CREATE TABLE reminders (
    id VARCHAR(36) PRIMARY KEY,
    member_id VARCHAR(36) NOT NULL,
    type ENUM('vaccine','checkup','review','medication') NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    scheduled_date DATE NOT NULL,
    status ENUM('pending','completed','overdue') DEFAULT 'pending',
    completed_date DATE,
    related_indicator VARCHAR(50),
    related_report_id VARCHAR(36),
    priority ENUM('critical','high','normal','low') DEFAULT 'normal',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
    INDEX idx_member_status (member_id, status),
    INDEX idx_scheduled (scheduled_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2.8 AI 对话表 (`ai_conversations`)

```sql
CREATE TABLE ai_conversations (
    id VARCHAR(36) PRIMARY KEY,
    member_id VARCHAR(36) NOT NULL,
    page_context VARCHAR(50),
    messages JSON NOT NULL DEFAULT '[]',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
    INDEX idx_member_updated (member_id, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2.9 疫苗记录表 (`vaccine_records`)

```sql
CREATE TABLE vaccine_records (
    id VARCHAR(36) PRIMARY KEY,
    member_id VARCHAR(36) NOT NULL,
    vaccine_name VARCHAR(100) NOT NULL,
    dose INT NOT NULL DEFAULT 1,
    scheduled_date DATE NOT NULL,
    actual_date DATE,
    status ENUM('completed','pending','upcoming','overdue') DEFAULT 'pending',
    location VARCHAR(100),
    batch_no VARCHAR(50),
    reaction TEXT,
    is_custom BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
    INDEX idx_member_status (member_id, status),
    INDEX idx_scheduled (scheduled_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 三、索引策略

| 表 | 索引 | 用途 |
|---|------|------|
| `indicator_data` | `(member_id, indicator_key, record_date)` | 指标历史查询（最频繁） |
| `indicator_data` | `(member_id, record_date)` | 时间轴加载 |
| `indicator_data` | `(status)` | 异常指标统计 |
| `health_events` | `(member_id, event_date)` | 时间轴分页 |
| `reports` | `(member_id, report_date)` | 报告列表 |
| `reminders` | `(member_id, status)` | 待办提醒查询 |
| `reminders` | `(scheduled_date)` | 定时任务扫描 |
| `members` | `(family_id)` | 家庭成员查询 |
| `members` | `(wx_openid)` | 微信登录查询 |

---

## 四、字段说明与约束

### 4.1 状态枚举映射

**`indicator_data.status`**（后端 4 级状态）：
| 值 | 含义 | 前端映射 |
|----|------|---------|
| `normal` | 在正常范围内 | 🟢 正常 |
| `low` | 低于参考范围 | 🟡 注意（文案显示"偏低"） |
| `high` | 高于参考范围 | 🟡 注意（文案显示"偏高"） |
| `critical` | 偏离 30% 以上危急值 | 🔴 严重异常 |

**`reports.ocr_status`**：
| 值 | 含义 |
|----|------|
| `pending` | 等待处理 |
| `processing` | OCR 进行中 |
| `completed` | 识别完成 |
| `failed` | 识别失败（重试 3 次后） |

**`hospital_events.status`**：
| 值 | 含义 |
|----|------|
| `active` | 住院中 |
| `discharged` | 已出院 |

**`members.role`**（家庭角色，已简化为两级）：
| 值 | 含义 | 权限 |
|----|------|------|
| `creator` | 家庭创建者/管理员 | 可编辑全部成员数据、邀请家人、移除成员 |
| `member` | 家人 | 可查看全部成员数据，仅可编辑自己创建的内容 |

### 4.2 JSON 字段约定

- `members.allergies`：`["青霉素", "花生"]` — 字符串数组
- `members.chronic_diseases`：`["高血压", "2型糖尿病"]` — 字符串数组
- `members.subscription_status`：`{"daily_digest": true, "urgent_alert": false}` — 模板名 → 布尔值
- `reports.images`：`["https://oss.example.com/reports/xxx.jpg"]` — 图片 URL 数组
- `reports.extracted_indicators`：`[{"name": "血红蛋白", "value": 120, "unit": "g/L", ...}]` — AI 提取的原始指标
- `hospital_events.key_nodes`：`[{"date": "2026-05-01", "event": "手术", "notes": "..."}]`
- `hospital_events.watch_indicators`：`["systolic_bp", "fasting_glucose"]` — 关注指标 key 数组
- `ai_conversations.messages`：`[{"role": "user", "content": "..."}, {"role": "ai", "content": "..."}]`

### 4.3 软删除约定

- `members` 表暂不设 `deleted_at` 字段（需物理删除时先记录到 `deleted_members_archive` 归档表）
- 家庭共享中"移除成员"操作：级联删除该成员的全部 `indicator_data`、`reports`、`health_events` 等关联数据（通过外键 `ON DELETE CASCADE`）
- 账号注销流程：`DELETE /api/members/me` 标记 `members` 为待删除状态，30 天后物理清除

### 4.4 数据类型规范

- 主键统一使用 `VARCHAR(36)` UUID，程序生成
- 金额/数值统一使用 `DECIMAL(10,3)`，保留 3 位小数
- 百分比使用 `DECIMAL(5,2)`，如 `25.00` 表示 25%
- 日期使用 `DATE`，日期时间使用 `DATETIME`
- JSON 字段使用 MySQL 8.0 原生 JSON 类型，配合 `->>` 操作符查询
- 所有表统一 `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4`
