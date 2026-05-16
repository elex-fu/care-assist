# E2E 测试（Minium）

## 环境要求

- WeChat Developer Tools（微信开发者工具）Mac/Windows
- Python 3.11+
- 后端服务已启动：`./scripts/dev-start.sh`
- Minium 已安装：`pip install minium`

## 配置

`minium.json` 中已配置：
- `project_path`: 小程序项目路径
- `dev_tool_path`: 微信开发者工具 CLI 路径（Mac 默认路径）

如果微信开发者工具安装路径不同，请修改 `dev_tool_path`。

## 运行

```bash
cd e2e
minitest -c minium.json -g test_core_path.py
```

## 核心路径覆盖

| 步骤 | 测试方法 | 说明 |
|------|----------|------|
| 登录 | `test_01_login` | 微信授权登录，获取 JWT |
| 首次引导 | `test_02_onboarding` | 创建家庭、添加首个成员 |
| 添加成员 | `test_03_add_member` | 从首页添加新家庭成员 |
| 上传报告 | `test_04_upload_report` | 拍照/选图上传，触发 OCR |
| 查看指标 | `test_05_view_indicator` | 指标列表、趋势图 |
| AI 对话 | `test_06_ai_chat` | 向 AI 提问，接收流式回答 |

## 注意事项

- OCR 步骤使用 mock 模式，不依赖真实 AI 服务
- 测试前确保 `app.json` 中 `pages/index/index` 为首页
- 测试会调用 `clearStorageSync` 清除本地缓存
- 建议在干净的开发者工具实例中运行
