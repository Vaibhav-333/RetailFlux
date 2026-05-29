"""Production-grade Redis cache with thundering herd protection, compression,
stale-while-revalidate, hit/miss metrics, SCAN-based stats, and request coalescing.

Key namespace: ``rf:cache:{category}:{identifier}``
Lock namespace: ``rf:lock:{key}``
Metrics namespace: ``rf:metrics:cache``
"""
import asyncio
import gzip
import json
import time
from functools import wraps
from typing import Any, Callable, Coroutine, Optional, TypeVar

import structlog

logger = structlog.get_logger()

# ── TTL constants ──────────────────────────────────────────────────────────────
ANALYTICS_TTL = 300       # 5 min  — analytics aggregations
INSIGHTS_TTL = 1800       # 30 min — LLM insight calls are expensive
FORECAST_TTL = 7200       # 2 hr   — Prophet / Holt-Winters fits are very expensive
STALE_EXTENSION = 60      # Extra seconds to keep stale data while revalidating
LOCK_TTL = 10             # Max seconds to hold a computation lock
COMPRESS_THRESHOLD = 1024  # Compress payloads larger than 1 KB

_PREFIX = "rf:cache"
_LOCK_PREFIX = "rf:lock"
_METRICS_KEY = "rf:metrics:cache"

# ── In-process request coalescing ──────────────────────────────────────────────
_inflight: dict[str, asyncio.Future[Any]] = {}

T = TypeVar("T")


# ── Key builders ───────────────────────────────────────────────────────────────

def analytics_key(dept: str, company_id: str, date_from: str, date_to: str) -> str:
    return f"{_PREFIX}:analytics:{dept}:{company_id}:{date_from}:{date_to}"


def inventory_key(name: str, company_id: str) -> str:
    """Cache key for inventory aggregations that are snapshot-based (no date range)."""
    return f"{_PREFIX}:inventory:{name}:{company_id}"


def summary_key(company_id: str) -> str:
    return f"{_PREFIX}:summary:{company_id}"


def insights_key(company_id: str) -> str:
    return f"{_PREFIX}:insights:{company_id}"


def forecast_key(company_id: str) -> str:
    return f"{_PREFIX}:forecast:top-skus:{company_id}"


# ── Core operations ────────────────────────────────────────────────────────────

async def get_json(key: str) -> Optional[Any]:
    """Return parsed JSON from Redis, or ``None`` on miss / error.
    Transparently decompresses gzip payloads. Tracks hit/miss metrics."""
    try:
        from app.core.redis_client import get_redis
        r = await get_redis()
        raw = await r.get(key)
        if raw is not None:
            await _record_metric(r, "hit")
            logger.debug("cache_hit", key=key)
            return _deserialize(raw)
        await _record_metric(r, "miss")
    except Exception as exc:
        logger.warning("cache_get_failed", key=key, error=str(exc))
    return None


async def get_json_with_stale(key: str) -> tuple[Optional[Any], bool]:
    """Return (data, is_stale). Checks the stale shadow key if primary is expired.
    Returns (None, False) on complete miss."""
    try:
        from app.core.redis_client import get_redis
        r = await get_redis()

        raw = await r.get(key)
        if raw is not None:
            await _record_metric(r, "hit")
            return _deserialize(raw), False

        stale_raw = await r.get(f"{key}:stale")
        if stale_raw is not None:
            await _record_metric(r, "stale_hit")
            logger.debug("cache_stale_hit", key=key)
            return _deserialize(stale_raw), True

        await _record_metric(r, "miss")
    except Exception as exc:
        logger.warning("cache_get_stale_failed", key=key, error=str(exc))
    return None, False


async def set_json(key: str, value: Any, ttl: int = ANALYTICS_TTL) -> None:
    """Serialize value to JSON, compress if large, store with TTL.
    Also writes a stale shadow copy with extended TTL for SWR."""
    try:
        from app.core.redis_client import get_redis
        r = await get_redis()
        payload = _serialize(value)
        pipe = r.pipeline()
        pipe.setex(key, ttl, payload)
        pipe.setex(f"{key}:stale", ttl + STALE_EXTENSION, payload)
        await pipe.execute()
        logger.debug("cache_set", key=key, ttl=ttl, size=len(payload))
    except Exception as exc:
        logger.warning("cache_set_failed", key=key, error=str(exc))


async def delete_pattern(pattern: str) -> int:
    """Delete all keys matching ``pattern`` using SCAN (non-blocking). Returns count deleted."""
    try:
        from app.core.redis_client import get_redis
        r = await get_redis()
        deleted = 0
        cursor = 0
        while True:
            cursor, keys = await r.scan(cursor=cursor, match=pattern, count=200)
            if keys:
                # Also delete stale shadow keys
                stale_keys = [f"{k}:stale" for k in keys]
                pipe = r.pipeline()
                pipe.delete(*keys)
                pipe.delete(*stale_keys)
                results = await pipe.execute()
                deleted += results[0] + results[1]
            if cursor == 0:
                break
        if deleted > 0:
            logger.info("cache_invalidated", pattern=pattern, count=deleted)
        return deleted
    except Exception as exc:
        logger.warning("cache_delete_failed", pattern=pattern, error=str(exc))
    return 0


# ── Thundering herd protection ─────────────────────────────────────────────────

async def acquire_lock(key: str, ttl: int = LOCK_TTL) -> bool:
    """Try to acquire a distributed lock. Returns True if acquired."""
    try:
        from app.core.redis_client import get_redis
        r = await get_redis()
        lock_key = f"{_LOCK_PREFIX}:{key}"
        acquired = await r.set(lock_key, "1", nx=True, ex=ttl)
        return acquired is not None
    except Exception:
        return True  # On Redis failure, allow computation (no protection, but no deadlock)


async def release_lock(key: str) -> None:
    """Release a distributed lock."""
    try:
        from app.core.redis_client import get_redis
        r = await get_redis()
        await r.delete(f"{_LOCK_PREFIX}:{key}")
    except Exception:
        pass


# ── Request coalescing ─────────────────────────────────────────────────────────

async def coalesce(key: str, compute_fn: Callable[[], Coroutine[Any, Any, T]]) -> T:
    """If another coroutine is already computing the same key in this process,
    wait for its result instead of duplicating the work."""
    if key in _inflight:
        return await _inflight[key]

    future: asyncio.Future[Any] = asyncio.get_event_loop().create_future()
    _inflight[key] = future
    try:
        result = await compute_fn()
        future.set_result(result)
        return result
    except Exception as exc:
        future.set_exception(exc)
        raise
    finally:
        _inflight.pop(key, None)


# ── Cache-aside decorator ──────────────────────────────────────────────────────

def cached(
    key_fn: Callable[..., str],
    ttl: int = ANALYTICS_TTL,
    model_class: Optional[type] = None,
    stale_while_revalidate: bool = True,
):
    """Decorator: cache-aside with thundering herd protection, SWR, and coalescing.

    Usage::

        @cached(key_fn=lambda cid, **kw: analytics_key("sales", cid, kw["df"], kw["dt"]),
                ttl=ANALYTICS_TTL, model_class=SalesKpisOut)
        async def get_sales_kpis(company_id, date_from, date_to): ...
    """
    def decorator(fn: Callable[..., Coroutine[Any, Any, Any]]):
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = key_fn(*args, **kwargs)

            if stale_while_revalidate:
                data, is_stale = await get_json_with_stale(cache_key)
            else:
                data = await get_json(cache_key)
                is_stale = False

            if data is not None and not is_stale:
                return model_class(**data) if model_class else data

            async def _compute():
                locked = await acquire_lock(cache_key)
                try:
                    if not locked:
                        # Another process is computing — wait briefly then check cache
                        await asyncio.sleep(0.5)
                        retry = await get_json(cache_key)
                        if retry is not None:
                            return model_class(**retry) if model_class else retry

                    result = await fn(*args, **kwargs)
                    dump = result.model_dump() if hasattr(result, "model_dump") else result
                    await set_json(cache_key, dump, ttl)
                    return result
                finally:
                    if locked:
                        await release_lock(cache_key)

            if is_stale and data is not None:
                # Serve stale, trigger background revalidation
                asyncio.create_task(_compute())
                return model_class(**data) if model_class else data

            return await coalesce(cache_key, _compute)

        wrapper.__wrapped__ = fn  # type: ignore[attr-defined]
        return wrapper
    return decorator


# ── Stats (SCAN-based, non-blocking) ──────────────────────────────────────────

async def get_stats() -> dict[str, Any]:
    """Return key counts by category using SCAN (non-blocking).
    Also returns hit/miss rates and Redis health."""
    try:
        from app.core.redis_client import get_redis
        r = await get_redis()

        # Count keys by category via SCAN
        by_category: dict[str, int] = {}
        total_keys = 0
        cursor = 0
        while True:
            cursor, keys = await r.scan(cursor=cursor, match=f"{_PREFIX}:*", count=500)
            for k in keys:
                # Skip stale shadow keys in the count
                if k.endswith(":stale"):
                    continue
                total_keys += 1
                parts = k.split(":")
                cat = parts[2] if len(parts) >= 3 else "other"
                by_category[cat] = by_category.get(cat, 0) + 1
            if cursor == 0:
                break

        # Metrics
        metrics = await _get_metrics(r)

        # Health
        start = time.monotonic()
        await r.ping()
        latency_ms = round((time.monotonic() - start) * 1000, 2)

        return {
            "total_keys": total_keys,
            "by_category": by_category,
            "metrics": metrics,
            "health": {"status": "healthy", "latency_ms": latency_ms},
        }
    except Exception as exc:
        logger.warning("cache_stats_failed", error=str(exc))
        return {
            "total_keys": 0,
            "by_category": {},
            "metrics": {"hits": 0, "misses": 0, "stale_hits": 0, "hit_rate": 0.0},
            "health": {"status": "unhealthy", "latency_ms": -1, "error": str(exc)},
        }


async def health_check() -> dict[str, Any]:
    """Quick Redis health check with latency measurement."""
    try:
        from app.core.redis_client import get_redis
        r = await get_redis()
        start = time.monotonic()
        await r.ping()
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        info = await r.info(section="memory")
        return {
            "status": "healthy",
            "latency_ms": latency_ms,
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "connected_clients": (await r.info(section="clients")).get("connected_clients", 0),
        }
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc), "latency_ms": -1}


# ── Cache warming ─────────────────────────────────────────────────────────────

async def warm_analytics_cache(company_id: str) -> dict[str, bool]:
    """Pre-populate analytics caches for a company. Call after invalidation
    or on deploy to avoid cold-start latency for users."""
    results: dict[str, bool] = {}
    try:
        from app.domains.analytics.sales_service import get_sales_kpis
        from app.domains.analytics.marketing_service import get_marketing_kpis
        from app.domains.analytics.operations_service import get_operations_kpis
        from app.domains.analytics.finance_service import get_finance_kpis
        from app.domains.analytics.procurement_service import get_procurement_kpis

        services = {
            "sales": get_sales_kpis,
            "marketing": get_marketing_kpis,
            "operations": get_operations_kpis,
            "finance": get_finance_kpis,
            "procurement": get_procurement_kpis,
        }

        tasks = {name: svc(company_id) for name, svc in services.items()}
        outcomes = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for name, outcome in zip(tasks.keys(), outcomes):
            results[name] = not isinstance(outcome, Exception)
            if isinstance(outcome, Exception):
                logger.warning("cache_warm_failed", dept=name, error=str(outcome))

        logger.info("cache_warmed", company_id=company_id, results=results)
    except Exception as exc:
        logger.warning("cache_warm_error", company_id=company_id, error=str(exc))
    return results


# ── Sync invalidation for Celery workers ──────────────────────────────────────

def invalidate_company_sync(company_id: str) -> None:
    """Sync version for Celery workers — delete all caches for a company using pipelines."""
    try:
        import redis as sync_redis
        from app.core.config import settings

        r = sync_redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        patterns = [
            f"{_PREFIX}:analytics:*:{company_id}:*",
            f"{_PREFIX}:summary:{company_id}",
            f"{_PREFIX}:insights:{company_id}",
            f"{_PREFIX}:forecast:top-skus:{company_id}",
        ]
        total = 0
        for pat in patterns:
            cursor = 0
            while True:
                cursor, keys = r.scan(cursor=cursor, match=pat, count=200)
                if keys:
                    stale_keys = [f"{k}:stale" for k in keys]
                    pipe = r.pipeline()
                    pipe.delete(*keys)
                    pipe.delete(*stale_keys)
                    results = pipe.execute()
                    total += results[0] + results[1]
                if cursor == 0:
                    break
        r.close()
        if total > 0:
            logger.info("cache_invalidated_sync", company_id=company_id, total=total)
    except Exception as exc:
        logger.warning("cache_invalidate_sync_failed", company_id=company_id, error=str(exc))


# ── Internal helpers ───────────────────────────────────────────────────────────

def _serialize(value: Any) -> str:
    """JSON-encode, optionally gzip for large payloads.
    Returns a string: plain JSON or base64-encoded gzip prefixed with 'gz:'."""
    raw = json.dumps(value, default=str)
    if len(raw) >= COMPRESS_THRESHOLD:
        compressed = gzip.compress(raw.encode("utf-8"), compresslevel=6)
        import base64
        return "gz:" + base64.b64encode(compressed).decode("ascii")
    return raw


def _deserialize(raw: str) -> Any:
    """Decode JSON, decompressing gzip if prefixed with 'gz:'."""
    if raw.startswith("gz:"):
        import base64
        compressed = base64.b64decode(raw[3:])
        decompressed = gzip.decompress(compressed).decode("utf-8")
        return json.loads(decompressed)
    return json.loads(raw)


async def _record_metric(r: Any, event: str) -> None:
    """Increment a hit/miss/stale_hit counter in Redis hash (fire-and-forget)."""
    try:
        await r.hincrby(_METRICS_KEY, event, 1)
    except Exception:
        pass


async def _get_metrics(r: Any) -> dict[str, Any]:
    """Read hit/miss/stale metrics from Redis hash."""
    try:
        raw = await r.hgetall(_METRICS_KEY)
        hits = int(raw.get("hit", 0))
        misses = int(raw.get("miss", 0))
        stale_hits = int(raw.get("stale_hit", 0))
        total = hits + misses + stale_hits
        return {
            "hits": hits,
            "misses": misses,
            "stale_hits": stale_hits,
            "hit_rate": round(hits / total, 4) if total > 0 else 0.0,
            "total_lookups": total,
        }
    except Exception:
        return {"hits": 0, "misses": 0, "stale_hits": 0, "hit_rate": 0.0, "total_lookups": 0}
