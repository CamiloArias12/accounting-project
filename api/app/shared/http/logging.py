"""Structured logging with a per-request identifier.

Every log line carries the request id, so a single call can be followed across
lines and across replicas. The id is echoed back in `X-Request-ID`, which is
what makes a user-reported error traceable.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_ID_HEADER = "X-Request-ID"

#: Read by the formatter; a ContextVar keeps it correct under concurrency.
request_id: ContextVar[str] = ContextVar("request_id", default="-")

_RESERVED = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id.get(),
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
        }

        # Anything passed via `extra=` rides along.
        payload.update({k: v for k, v in record.__dict__.items() if k not in _RESERVED})

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    # uvicorn ships its own handlers; drop them so everything is JSON.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER)
        # An id from upstream is reused, so a trace survives across services.
        current = incoming or uuid.uuid4().hex
        token = request_id.set(current)
        started = time.perf_counter()

        log = logging.getLogger("app.request")
        try:
            response = await call_next(request)
        except Exception:
            log.exception(
                "request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": _elapsed(started),
                },
            )
            raise
        else:
            response.headers[REQUEST_ID_HEADER] = current
            log.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": _elapsed(started),
                },
            )
            return response
        finally:
            # Reset last: the log lines above must still see the id.
            request_id.reset(token)


def _elapsed(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)
