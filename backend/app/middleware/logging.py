import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger("app.middleware.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    请求/响应日志中间件。

    记录每个HTTP请求的完整生命周期：
    - 请求ID（X-Request-ID）注入与传递
    - 请求方法、路径、查询参数、客户端IP
    - 响应状态码、处理耗时
    - 4xx/5xx 错误额外记录详细信息
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成或复用请求ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:16])
        request.state.request_id = request_id

        # 记录请求开始时间
        start_time = time.perf_counter()
        client_host = request.client.host if request.client else "-"
        method = request.method
        path = request.url.path
        query = str(request.query_params) if request.query_params else ""

        # 将请求ID绑定到logger（通过extra传入）
        extra = {"request_id": request_id}

        logger.info(
            f"→ {method} {path}{'?' + query if query else ''} | client={client_host}",
            extra=extra,
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            # 未捕获的异常，记录为ERROR并重新抛出
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"✗ {method} {path} | error={type(exc).__name__}: {exc} | duration={duration_ms:.2f}ms",
                exc_info=True,
                extra=extra,
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000
        status_code = response.status_code

        # 在响应头中返回请求ID，方便客户端追踪
        response.headers["X-Request-ID"] = request_id

        # 根据状态码选择日志级别
        if status_code >= 500:
            log_method = logger.error
        elif status_code >= 400:
            log_method = logger.warning
        else:
            log_method = logger.info

        log_method(
            f"← {method} {path} | status={status_code} | duration={duration_ms:.2f}ms",
            extra=extra,
        )

        return response
