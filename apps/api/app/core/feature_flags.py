"""Feature flag resolution with Redis caching (60 s TTL).

Lookup order:
  1. Redis (60 s TTL)
  2. Postgres — company-specific row first, then global row (company_id IS NULL)
  3. Default → False

Usage::

    from app.core.feature_flags import is_enabled

    if await is_enabled(db, "scenarios", current_user.company_id):
        ...
"""
from __future__ import annotations

import json
import uuid
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

_TTL = 60  # seconds
_PREFIX = "rf:ff"


def _cache_key(key: str, company_id: uuid.UUID | None) -> str:
    cid = str(company_id) if company_id else "global"
    return f"{_PREFIX}:{cid}:{key}"


async def is_enabled(
    db: AsyncSession,
    key: str,
    company_id: uuid.UUID | None = None,
) -> bool:
    """Return True if *key* is enabled for *company_id* (or globally)."""
    from app.core.redis_client import get_redis  # noqa: PLC0415

    redis = await get_redis()
    cache_k = _cache_key(key, company_id)

    try:
        cached = await redis.get(cache_k)
        if cached is not None:
            return json.loads(cached)
    except Exception as exc:
        logger.warning("ff_cache_read_failed", key=key, error=str(exc))

    try:
        result = await db.execute(
            text("""
                SELECT enabled FROM app.feature_flags
                WHERE key = :key
                  AND (company_id = :cid OR company_id IS NULL)
                ORDER BY (company_id IS NOT NULL) DESC
                LIMIT 1
            """),
            {"key": key, "cid": str(company_id) if company_id else None},
        )
        row = result.fetchone()
        enabled = bool(row[0]) if row else False
    except Exception as exc:
        logger.warning("ff_db_read_failed", key=key, error=str(exc))
        enabled = False

    try:
        await redis.set(cache_k, json.dumps(enabled), ex=_TTL)
    except Exception as exc:
        logger.warning("ff_cache_write_failed", key=key, error=str(exc))

    return enabled


async def list_flags(
    db: AsyncSession,
    company_id: uuid.UUID | None = None,
) -> list[dict[str, Any]]:
    """Return all flags visible to *company_id* (company-specific + global)."""
    try:
        result = await db.execute(
            text("""
                SELECT id, company_id, key, enabled, payload, created_at, updated_at
                FROM app.feature_flags
                WHERE company_id = :cid OR company_id IS NULL
                ORDER BY key, (company_id IS NOT NULL) DESC
            """),
            {"cid": str(company_id) if company_id else None},
        )
        return [
            {
                "id": str(r[0]),
                "company_id": str(r[1]) if r[1] else None,
                "key": r[2],
                "enabled": bool(r[3]),
                "payload": r[4],
                "created_at": r[5].isoformat() if r[5] else None,
                "updated_at": r[6].isoformat() if r[6] else None,
            }
            for r in result.fetchall()
        ]
    except Exception as exc:
        logger.warning("ff_list_failed", error=str(exc))
        return []


async def set_flag(
    db: AsyncSession,
    key: str,
    enabled: bool,
    company_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Upsert a feature flag and bust the Redis cache."""
    from app.core.redis_client import get_redis  # noqa: PLC0415

    payload_json = json.dumps(payload or {})

    if company_id is None:
        await db.execute(
            text("""
                INSERT INTO app.feature_flags (company_id, key, enabled, payload, updated_at)
                VALUES (NULL, :key, :enabled, :payload::jsonb, now())
                ON CONFLICT (key) WHERE company_id IS NULL
                DO UPDATE SET enabled    = EXCLUDED.enabled,
                              payload    = EXCLUDED.payload,
                              updated_at = now()
            """),
            {"key": key, "enabled": enabled, "payload": payload_json},
        )
    else:
        await db.execute(
            text("""
                INSERT INTO app.feature_flags (company_id, key, enabled, payload, updated_at)
                VALUES (:cid, :key, :enabled, :payload::jsonb, now())
                ON CONFLICT (company_id, key) WHERE company_id IS NOT NULL
                DO UPDATE SET enabled    = EXCLUDED.enabled,
                              payload    = EXCLUDED.payload,
                              updated_at = now()
            """),
            {"cid": str(company_id), "key": key, "enabled": enabled, "payload": payload_json},
        )

    await db.commit()

    redis = await get_redis()
    try:
        await redis.delete(_cache_key(key, company_id))
    except Exception:
        pass

    return {"key": key, "enabled": enabled, "company_id": str(company_id) if company_id else None}
