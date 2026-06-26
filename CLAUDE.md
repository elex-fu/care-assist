# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project Identity

**家庭智能健康助手** — native WeChat Mini Program + Python/FastAPI backend for family health records, indicators, reports, medications, hospital visits, vaccines, and AI-assisted health Q&A.

- `miniprogram/` — native 微信小程序（非 Uni-app）。
- `backend/` — Python 3.11+ FastAPI, SQLAlchemy 2.0 async, MySQL, Redis, Celery, Alembic.
- `e2e/` — Minium 小程序 UI E2E tests.

## Development Constraints

- **Backend:** Python >=3.11, FastAPI >=0.110, SQLAlchemy 2.0 async, MySQL 8.0+ (dev port `3308` for tests), Alembic for migrations.
- **Frontend:** native 微信小程序，不使用第三方框架；新页面必须在 `app.json` 对应分包 `pages` 中注册。
- **Tests:** pytest + pytest-asyncio，TDD 风格；**必须使用 `python -m pytest`，直接执行 `pytest` 会因路径问题报错。**
- **Lint:** ruff line-length 100，mypy strict。
- **Commits:** `feat(scope): description`，结尾加 `Co-Authored-By: Claude <noreply@anthropic.com>`。
- **Secrets:** API key / 敏感信息只走 `.env`，不提交 git。
- **Registration:** 新增 API 必须在 `backend/app/main.py` 注册；新增数据模型必须通过 Alembic 生成迁移。
- **Cleanup:** 不要 `git add -A` 误提交 `.mysql_data/`、`uploads/`、`e2e/screenshots/` 等目录。

## Architecture Quick Reference

```
backend/app/
├── api/        # FastAPI routers, mounted under /api in main.py
├── core/       # Domain logic (indicator_engine, ai_service, ocr_service, security, logging)
├── db/         # Async SQLAlchemy engine/session and Base
├── models/     # SQLAlchemy ORM models
├── schemas/    # Pydantic request/response models
├── services/   # Higher-level orchestration
└── middleware/ # Request logging with request IDs
```

`backend/app/main.py` wires routers with `/api` prefix, mounts `/static`, registers global exception handlers. `BusinessException` is the domain error type converted to structured JSON.

## Core Domain

- **Family** → top-level group.
- **Member** → person in family, role `creator`/`member`, type `adult`/`child`/`elderly`.
- **IndicatorData** → numeric health indicators with status (`normal`/`low`/`high`/`critical`).
- **Report** → uploaded medical images + OCR-extracted indicators.
- **Hospital / HealthEvent / Medication / Vaccine / Reminder / AIConversation** — member-linked records.

Permissions are enforced via `app/core/permissions.py` patterns: verify member belongs to current member's family.

## Key Implementation Patterns

- **Backend API:** FastAPI `APIRouter`, `ResponseWrapper[T]`, `get_current_member` dependency, `AsyncSession` DB injection.
- **Frontend:** `Page({ data, onLoad, loadData, ... })`, use `utils/api.js` (`api.get/post/del/uploadFile`), `utils/store.js`, `utils/format.js`.
- **AI/OCR:** Provider abstraction under `backend/app/ai/`; OCR tests run in `mock` mode by default (`OCR_PROVIDER=mock`).
- **WeChat auth:** JWT-based; `code2session` via WeChat. Tests use `auth_client` / `member_client` fixtures.

## AI Assistant Notes

- Do not add generic advice sections (testing tips, support contacts, etc.) unless explicitly present in project files.
- This project has no `.cursorrules` / `.cursor/rules/` or `.github/copilot-instructions.md`.
- Check `TODOS.md` before starting large features.
- Prefer focused files; split by responsibility, not by technical layer.
- For multi-step implementation, use `superpowers:writing-plans` first, then `superpowers:subagent-driven-development` or `superpowers:executing-plans`.
