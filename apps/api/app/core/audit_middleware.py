"""Audit middleware — records every mutating request to app.audit_log (fire-and-forget).

Captures request_id from X-Request-ID header and diff (request body for PATCH/PUT)
for change-tracking purposes.
"""
import asyncio
import json
import uuid
from typing import Any, Optional

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()

_MUTATING = {"POST", "PATCH", "PUT", "DELETE"}
_SKIP_PREFIXES = ("/metrics", "/health", "/docs", "/redoc", "/openapi")
_DIFF_METHODS = {"PATCH", "PUT"}
_MAX_BODY_SIZE = 65_536


def _parse_resource(path: str) -> tuple[str, Optional[str]]:
    """Derive (resource, resource_id) from an API path.

    /api/v1/users/abc-123        → ("users",    "abc-123")
    /api/v1/analytics/sales      → ("analytics", "sales")
    /api/v1/uploads              → ("uploads",   None)
    """
    parts = [p for p in path.split("/") if p]
    while parts and parts[0] in ("api", "v1"):
        parts = parts[1:]
    if not parts:
        return ("unknown", None)
    resource = parts[0]
    resource_id = parts[1] if len(parts) > 1 else None
    return (resource, resource_id)


def _get_client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _decode_user_id(request: Request) -> Optional[uuid.UUID]:
    """Fast JWT decode (no DB) — returns user UUID or None."""
    try:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth.split(" ", 1)[1]
        from app.core.security import decode_token  # noqa: PLC0415
        payload = decode_token(token)
        sub = payload.get("sub")
        return uuid.UUID(sub) if sub else None
    except Exception:
        return None


async def _read_body(request: Request) -> Optional[dict[str, Any]]:
    """Read and parse the request body for diff capture. Returns None on failure."""
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" not in content_type:
            return None
        body = await request.body()
        if len(body) > _MAX_BODY_SIZE:
            return None
        return json.loads(body)
    except Exception:
        return None


async def _write_audit(
    user_id: Optional[uuid.UUID],
    action: str,
    resource: str,
    resource_id: Optional[str],
    ip: Optional[str],
    ua: Optional[str],
    request_id: Optional[str],
    diff: Optional[dict[str, Any]],
) -> None:
    try:
        from app.core.database import AsyncSessionLocal  # noqa: PLC0415
        from app.models.audit import AuditLog  # noqa: PLC0415

        async with AsyncSessionLocal() as db:
            entry = AuditLog(
                user_id=user_id,
                action=action,
                resource=resource,
                resource_id=resource_id,
                ip=ip,
                ua=ua,
                request_id=request_id,
                diff=diff,
            )
            db.add(entry)
            await db.commit()
    except Exception as exc:
        logger.warning("audit_write_failed", error=str(exc))


class AuditMiddleware(BaseHTTPMiddleware):
    """Records mutating (POST/PATCH/PUT/DELETE) requests to audit_log after response."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        if request.method not in _MUTATING:
            return await call_next(request)
        if any(request.url.path.startswith(p) for p in _SKIP_PREFIXES):
            return await call_next(request)

        user_id = _decode_user_id(request)
        ip = _get_client_ip(request)
        ua = request.headers.get("User-Agent")
        request_id = request.headers.get("X-Request-ID")
        resource, resource_id = _parse_resource(request.url.path)

        diff: Optional[dict[str, Any]] = None
        if request.method in _DIFF_METHODS:
            diff = await _read_body(request)

        response = await call_next(request)

        if response.status_code < 500:
            asyncio.create_task(
                _write_audit(
                    user_id=user_id,
                    action=request.method,
                    resource=resource,
                    resource_id=resource_id,
                    ip=ip,
                    ua=ua,
                    request_id=request_id,
                    diff=diff,
                )
            )
        return response
