import logging
import logging.config
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings


class RequestIdFilter(logging.Filter):
    """注入请求ID到日志记录中，便于追踪单个请求的全链路日志。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = getattr(record, "request_id", "-")
        return True


class UTCFormatter(logging.Formatter):
    """使用UTC时间格式化日志，避免多时区部署时的混乱。"""

    converter = datetime.fromtimestamp

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat(timespec="milliseconds")


class JsonFormatter(logging.Formatter):
    """结构化JSON格式，便于ELK/Loki等日志系统采集和检索。"""

    def format(self, record: logging.LogRecord) -> str:
        import json

        log_obj: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id") and record.request_id != "-":
            log_obj["request_id"] = record.request_id
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False, default=str)


def _ensure_log_dir(log_path: str) -> None:
    """确保日志文件所在目录存在。"""
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)


def configure_logging() -> None:
    """
    配置全局日志系统。

    特性：
    - 控制台输出：人类可读格式，方便开发调试
    - 文件输出：按大小自动轮转，保留历史
    - JSON格式：生产环境可选，便于日志收集系统解析
    - 请求ID过滤：支持全链路日志追踪
    """
    log_level = settings.LOG_LEVEL.upper()
    log_dir = Path(settings.LOG_FILE_PATH).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # 根据环境选择格式
    if settings.LOG_FORMAT == "json":
        formatter_class = "app.core.logging.JsonFormatter"
    else:
        formatter_class = "app.core.logging.UTCFormatter"

    handlers: dict[str, dict[str, Any]] = {
        "console": {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": "standard",
            "stream": "ext://sys.stdout",
            "filters": ["request_id"],
        },
        "file_app": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "standard",
            "filename": str(log_dir / "app.log"),
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 10,
            "encoding": "utf-8",
            "filters": ["request_id"],
        },
        "file_error": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "standard",
            "filename": str(log_dir / "error.log"),
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 20,
            "encoding": "utf-8",
            "filters": ["request_id"],
        },
    }

    # 生产环境保留access日志文件（Uvicorn access日志单独收集）
    if settings.ENVIRONMENT in ("production", "staging"):
        handlers["file_access"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "access",
            "filename": str(log_dir / "access.log"),
            "maxBytes": 50 * 1024 * 1024,  # 50MB
            "backupCount": 5,
            "encoding": "utf-8",
        }

    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {
                "()": "app.core.logging.RequestIdFilter",
            },
        },
        "formatters": {
            "standard": {
                "()": formatter_class,
                "fmt": "%(asctime)s | %(levelname)-8s | %(request_id)s | %(name)s | %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            },
            "access": {
                "()": formatter_class,
                "fmt": "%(asctime)s | %(levelname)-8s | %(client_addr)s | %(request_line)s | %(status_code)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            },
        },
        "handlers": handlers,
        "loggers": {
            # 应用核心模块
            "app": {
                "level": log_level,
                "handlers": ["console", "file_app", "file_error"],
                "propagate": False,
            },
            # 第三方库日志级别抑制，避免噪音
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file_app"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console"],  # access日志由中间件统一处理
                "propagate": False,
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["console", "file_error"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING" if not settings.DEBUG else "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "celery": {
                "level": "INFO",
                "handlers": ["console", "file_app"],
                "propagate": False,
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console", "file_app", "file_error"],
        },
    }

    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """获取指定模块的logger，统一使用此函数避免直接调用logging.getLogger。"""
    return logging.getLogger(name)
