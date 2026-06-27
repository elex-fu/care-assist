import asyncio
from collections.abc import Coroutine
from typing import Any

import nest_asyncio


def run_async_task(coro: Coroutine[Any, Any, Any]) -> Any:
    """Run an async coroutine from a synchronous Celery task.

    Celery workers run sync code; this helper starts a new event loop when
    none is currently running. If it is called inside an existing event loop
    (for example during tests), ``nest_asyncio`` is applied so the coroutine
    can be executed synchronously on the current loop.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    nest_asyncio.apply(loop)
    return loop.run_until_complete(coro)
