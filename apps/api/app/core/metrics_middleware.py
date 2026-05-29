"""HTTP request metrics middleware — records timing and status to MongoDB api_metrics."""
import asyncio
import time
from datetime import datetime, timezone
from typing import Set

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()

_SKIP_PATHS: Set[str] = {
    "/metrics",
    "/health",
    "/api/v1/health",
    "/favicon.ico",
    "/docs",
    "/redoc",
    "/openapi.json",
}

_ttl_index_ensured = False


async def _ensure_ttl_index() -> None:
    global _ttl_index_ensured
    if _ttl_index_ensured:
        return
    try:
        from app.core.mongodb import get_mongo_db
        col = get_mongo_db()["api_metrics"]
        await col.create_index(
            "timestamp",
            expireAfterSeconds=7 * 24 * 3600,
            background=True,
        )
        _ttl_index_ensured = True
    except Exception as exc:
        logger.warning("metrics_ttl_index_failed", error=str(exc))


async def _record_metric(
    endpoint: str,
    method: str,
    status_code: int,
    duration_ms: float,
) -> None:
    try:
        await _ensure_ttl_index()
        from app.core.mongodb import get_mongo_db
        col = get_mongo_db()["api_metrics"]
        await col.insert_one({
            "timestamp": datetime.now(timezone.utc),
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "is_error": status_code >= 400,
        })
    except Exception as exc:
        logger.warning("metrics_record_failed", error=str(exc))


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    """Stamps every non-health request with timing data into MongoDB (fire-and-forget)."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        asyncio.create_task(
            _record_metric(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
        )
        return response
