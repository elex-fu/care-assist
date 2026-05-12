# 开发环境搭建指南

> 目标：从零到本地运行，预计 15 分钟。

---

## 前提条件

| 工具 | 版本 | 用途 |
|------|------|------|
| Docker + Docker Compose | v2.x | MySQL、Redis、后端服务 |
| Python | 3.11+ | 后端开发（可选，也可全用 Docker） |
| Node.js | 18+ | 前端工具链（可选） |
| 微信开发者工具 | 最新稳定版 | 小程序预览与调试 |
| Git | 任意 | 版本管理 |

---

## 1. 克隆与配置

```bash
git clone <repo-url>
cd care-assist

# 复制环境变量模板
cp .env.example .env
# 按需编辑 .env，至少确认 DATABASE_URL 和 REDIS_URL
```

---

## 2. 启动基础设施（MySQL + Redis）

```bash
docker-compose up -d mysql redis
```

验证：
```bash
docker ps
# 应看到 care-assist-mysql 和 care-assist-redis 状态为 healthy
```

---

## 3. 启动后端

### 方式 A：Docker（推荐，零本地依赖）

```bash
docker-compose up -d backend
```

后端运行于 http://localhost:8000，自带热重载。

### 方式 B：一键脚本（推荐本地开发）

项目提供了三个开发脚本：

```bash
# 一键启动：检测 MySQL/Redis，安装依赖，启动后端
./scripts/dev-start.sh

# 查看运行状态
./scripts/dev-status.sh

# 停止后端（保留 MySQL/Redis）
./scripts/dev-stop.sh
```

`dev-start.sh` 会自动：
- 检测端口占用
- 启动本地 MySQL（brew services 或 Docker）
- 启动本地 Redis（brew services 或 Docker，如不可用则跳过并警告）
- 创建 Python 虚拟环境并安装依赖
- 启动 FastAPI 并等待 health check 通过

### 方式 C：手动启动

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

验证后端：
```bash
curl http://localhost:8000/health
# 预期输出: {"status":"ok"}
```

---

## 4. 数据库迁移

首次建表：

```bash
cd backend

# 方式 A（本地 Python）
alembic revision --autogenerate -m "init"
alembic upgrade head

# 方式 B（Docker）
docker exec -it care-assist-backend alembic revision --autogenerate -m "init"
docker exec -it care-assist-backend alembic upgrade head
```

> **注意**：`--autogenerate` 需要先在 `app/models/` 中定义模型并导入到 `alembic/env.py`。在业务模型创建前，可先手动写 migration 脚本。

---

## 5. 启动前端（微信小程序）

1. 打开 **微信开发者工具**
2. 选择「导入项目」
3. 项目目录选择 `<repo-root>/miniprogram`
4. AppID 填写你自己的测试 AppID（或使用测试号）
5. 后端地址配置在 `miniprogram/app.js` 的 `globalData.apiBase`
   - 真机调试时改为局域网 IP，如 `http://192.168.1.x:8000`
   - 小程序预览时要求 HTTPS，需配置内网穿透或 staging 环境

---

## 6. 微信配置 Checklist

开发前必须在[微信公众平台](https://mp.weixin.qq.com/)完成：

- [ ] 注册小程序账号，获取 AppID 和 AppSecret，填入 `.env`
- [ ] 服务器域名配置（开发设置 → 服务器域名）
  - `request` 合法域名：`https://your-api-domain.com`
  - `socket` 合法域名：`wss://your-api-domain.com`
  - `uploadFile` 合法域名：`https://your-oss-domain.com`
  - `downloadFile` 合法域名：`https://your-cdn-domain.com`
- [ ] 业务域名配置（如果使用 web-view）
- [ ] 申请订阅消息模板（日常提醒、异常告警）
- [ ] 用户隐私保护指引设置（小程序后台 → 设置 → 用户隐私保护）
- [ ] 若为医疗类目，需准备相关资质并申请类目审核

---

## 7. 常用命令

```bash
# 查看日志
docker-compose logs -f backend

# 重启后端
docker-compose restart backend

# 进入 MySQL
docker exec -it care-assist-mysql mysql -ucare -pcarepass care_assist

# 进入 Redis
docker exec -it care-assist-redis redis-cli

# 代码检查（后端）
cd backend
ruff check .
mypy app

# 运行测试（后端）
pytest
```

---

## 8. 目录速查

```
care-assist/
├── backend/           # FastAPI 后端
│   ├── app/
│   │   ├── main.py    # 应用入口
│   │   ├── db/        # 数据库 session + 模型基类
│   │   ├── api/       # 路由（待实现）
│   │   ├── core/      # 异常、安全、引擎（待实现）
│   │   └── models/    # SQLAlchemy 模型（待实现）
│   ├── alembic/       # 数据库迁移
│   ├── tests/         # 测试（待实现）
│   ├── pyproject.toml # 依赖与工具配置
│   └── Dockerfile
├── miniprogram/       # 微信小程序
│   ├── app.js         # 全局逻辑
│   ├── app.json       # 全局配置 + 页面路由
│   ├── app.wxss       # 全局样式（CSS Variables）
│   ├── pages/         # 页面
│   └── project.config.json
├── docker-compose.yml # 基础设施编排
├── .env.example       # 环境变量模板
└── docs/              # 设计文档
    ├── design/        # 5 份设计文档
    └── SETUP.md       # 本文件
```

---

## 9. 常见问题

**Q: 后端启动报 `ModuleNotFoundError: No module named 'app'`**  
A: 确保在 `backend/` 目录内运行 `uvicorn`，或设置 `PYTHONPATH=.`。

**Q: 小程序真机调试无法连接后端**  
A: 开发者工具 → 详情 → 本地设置 → 勾选「不校验合法域名、web-view...」。真机预览需 HTTPS + 已配置域名。

**Q: Alembic autogenerate 没有检测到模型变更**  
A: 确保模型文件在 `alembic/env.py` 中被导入（如 `from app.models import *`），否则 Alembic 无法扫描到表定义。

**Q: 如何清空数据库重新开始？**  
A: `docker-compose down -v mysql` 会删除 MySQL 数据卷，然后重新 `docker-compose up -d mysql`。
