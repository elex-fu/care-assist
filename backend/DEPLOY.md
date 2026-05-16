# 部署指南

## 环境要求

- Docker & Docker Compose
- 域名 + SSL 证书（生产环境）
- 微信小程序 AppID + Secret

## 环境变量

```bash
# 必填
SECRET_KEY=your-random-secret-key
WECHAT_APPID=wx...
WECHAT_SECRET=...

# 可选（有默认值）
MYSQL_ROOT_PASSWORD=rootpass
MYSQL_PASSWORD=carepass
```

## 启动

```bash
cd backend
cp .env.example .env  # 编辑环境变量
docker-compose up -d
```

## 首次部署

```bash
# 运行数据库迁移
docker-compose exec app alembic upgrade head
```

## 小程序审核材料

- 隐私政策：`https://your-domain.com/static/privacy.html`
- 用户协议：`https://your-domain.com/static/terms.html`

## 健康检查

```bash
curl https://your-domain.com/health
```
