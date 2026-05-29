"""Tests for the production-grade Redis cache: hit/miss, compression, SWR,
thundering herd, coalescing, SCAN-based stats, warming, and management endpoints."""
import asyncio
import gzip
import json
import base64
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.user import User, UserRole

FAKE_UID = uuid.uuid4()
FAKE_CID = uuid.uuid4()


def _fake_ceo() -> MagicMock:
    u = MagicMock(spec=User)
    u.id = FAKE_UID
    u.email = "ceo@acme.com"
    u.name = "CEO"
    u.role = UserRole.CEO
    u.company_id = FAKE_CID
    u.is_active = True
    u.last_login_at = None
    u.prefs = None
    u.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return u


def _fake_sales() -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.role = UserRole.SALES
    u.company_id = FAKE_CID
    u.is_active = True
    return u


@pytest.fixture(autouse=True)
def _override_auth():
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = _fake_ceo
    yield
    app.dependency_overrides.clear()


# ── Serialization / compression tests ────────────────────────────────────────

def test_serialize_small_payload_is_plain_json():
    from app.core.cache import _serialize, _deserialize
    data = {"revenue": 100.5}
    raw = _serialize(data)
    assert not raw.startswith("gz:")
    assert _deserialize(raw) == data


def test_serialize_large_payload_is_compressed():
    from app.core.cache import _serialize, _deserialize, COMPRESS_THRESHOLD
    data = {"big_list": list(range(500))}
    raw = _serialize(data)
    assert raw.startswith("gz:")
    assert len(raw) < len(json.dumps(data))
    assert _deserialize(raw) == data


# ── get_json with hit/miss metrics ───────────────────────────────────────────

async def test_get_json_returns_value_on_cache_hit():
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=json.dumps({"total_revenue": 100.0}))
    mock_redis.hincrby = AsyncMock()

    with patch("app.core.redis_client.get_redis", new_callable=AsyncMock) as mock_get_redis:
        mock_get_redis.return_value = mock_redis
        from app.core.cache import get_json
        result = await get_json("rf:cache:analytics:sales:abc:2024-01-01:2024-01-31")

    assert result == {"total_revenue": 100.0}
    mock_redis.hincrby.assert_called_once_with("rf:metrics:cache", "hit", 1)


async def test_get_json_returns_none_on_cache_miss():
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.hincrby = AsyncMock()

    with patch("app.core.redis_client.get_redis", new_callable=AsyncMock) as mock_get_redis:
        mock_get_redis.return_value = mock_redis
        from app.core.cache import get_json
        result = await get_json("rf:cache:analytics:sales:abc:2024-01-01:2024-01-31")

    assert result is None
    mock_redis.hincrby.assert_called_once_with("rf:metrics:cache", "miss", 1)


async def test_get_json_decompresses_gzip_payload():
    data = {"items": list(range(100))}
    compressed = gzip.compress(json.dumps(data).encode("utf-8"), compresslevel=6)
    stored = "gz:" + base64.b64encode(compressed).decode("ascii")

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=stored)
    mock_redis.hincrby = AsyncMock()

    with patch("app.core.redis_client.get_redis", new_callable=AsyncMock) as mock_get_redis:
        mock_get_redis.return_value = mock_redis
        from app.core.cache import get_json
        result = await get_json("rf:cache:test:key")

    assert result == data


async def test_get_json_returns_none_when_redis_unavailable():
    with patch("app.core.redis_client.get_redis", side_effect=Exception("Connection refused")):
        from app.core.cache import get_json
        result = await get_json("rf:cache:test:any:key")
    assert result is None


# ── Stale-while-revalidate ───────────────────────────────────────────────────

async def test_get_json_with_stale_returns_fresh_on_primary_hit():
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=json.dumps({"fresh": True}))
    mock_redis.hincrby = AsyncMock()

    with patch("app.core.redis_client.get_redis", new_callable=AsyncMock) as mock_get_redis:
        mock_get_redis.return_value = mock_redis
        from app.core.cache import get_json_with_stale
        data, is_stale = await get_json_with_stale("rf:cache:test:key")

    assert data == {"fresh": True}
    assert is_stale is False


async def test_get_json_with_stale_returns_stale_on_shadow_hit():
    async def mock_get(key):
        if key.endswith(":stale"):
            return json.dumps({"stale": True})
        return None

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(side_effect=mock_get)
    mock_redis.hincrby = AsyncMock()

    with patch("app.core.redis_client.get_redis", new_callable=AsyncMock) as mock_get_redis:
        mock_get_redis.return_value = mock_redis
        from app.core.cache import get_json_with_stale
        data, is_stale = await get_json_with_stale("rf:cache:test:key")

    assert data == {"stale": True}
    assert is_stale is True


# ── set_json with pipeline + stale ──────────────────────────────────────────

async def test_set_json_writes_both_primary_and_stale_keys():
    mock_pipe = MagicMock()
    mock_pipe.setex = MagicMock()
    mock_pipe.execute = AsyncMock(return_value=[True, True])

    mock_redis = MagicMock()
    mock_redis.pipeline = MagicMock(return_value=mock_pipe)

    with patch("app.core.redis_client.get_redis", new_callable=AsyncMock) as mock_get_redis:
        mock_get_redis.return_value = mock_redis
        from app.core.cache import set_json, STALE_EXTENSION
        await set_json("rf:cache:test:key", {"v": 1}, ttl=300)

    assert mock_pipe.setex.call_count == 2
    calls = mock_pipe.setex.call_args_list
    assert calls[0][0][0] == "rf:cache:test:key"
    assert calls[0][0][1] == 300
    assert calls[1][0][0] == "rf:cache:test:key:stale"
    assert calls[1][0][1] == 300 + 60  # STALE_EXTENSION


async def test_set_json_swallows_redis_error():
    with patch("app.core.redis_client.get_redis", side_effect=Exception("Connection refused")):
        from app.core.cache import set_json
        await set_json("rf:cache:test:key", {"value": 1}, ttl=60)


# ── delete_pattern uses SCAN ─────────────────────────────────────────────────

async def test_delete_pattern_uses_scan_not_keys():
    mock_pipe = MagicMock()
    mock_pipe.delete = MagicMock()
    mock_pipe.execute = AsyncMock(return_value=[3, 3])

    mock_redis = MagicMock()
    mock_redis.scan = AsyncMock(return_value=(0, ["k1", "k2", "k3"]))
    mock_redis.pipeline = MagicMock(return_value=mock_pipe)

    with patch("app.core.redis_client.get_redis", new_callable=AsyncMock) as mock_get_redis:
        mock_get_redis.return_value = mock_redis
        from app.core.cache import delete_pattern
        count = await delete_pattern("rf:cache:analytics:sales:*")

    mock_redis.scan.assert_called()
    assert count == 6  # 3 primary + 3 stale


# ── Thundering herd (distributed lock) ───────────────────────────────────────

async def test_acquire_lock_success():
    mock_redis = MagicMock()
    mock_redis.set = AsyncMock(return_value=True)

    with patch("app.core.redis_client.get_redis", new_callable=AsyncMock) as mock_get_redis:
        mock_get_redis.return_value = mock_redis
        from app.core.cache import acquire_lock
        result = await acquire_lock("rf:cache:test:key")

    assert result is True
    mock_redis.set.assert_called_once_with("rf:lock:rf:cache:test:key", "1", nx=True, ex=10)


async def test_acquire_lock_fails_when_held():
    mock_redis = MagicMock()
    mock_redis.set = AsyncMock(return_value=None)

    with patch("app.core.redis_client.get_redis", new_callable=AsyncMock) as mock_get_redis:
        mock_get_redis.return_value = mock_redis
        from app.core.cache import acquire_lock
        result = await acquire_lock("rf:cache:test:key")

    assert result is False


# ── Request coalescing ───────────────────────────────────────────────────────

async def test_coalesce_deduplicates_concurrent_calls():
    call_count = 0

    async def expensive_compute():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return {"result": 42}

    from app.core.cache import coalesce

    results = await asyncio.gather(
        coalesce("test:key", expensive_compute),
        coalesce("test:key", expensive_compute),
        coalesce("test:key", expensive_compute),
    )

    assert call_count == 1
    assert all(r == {"result": 42} for r in results)


# ── Stats (SCAN-based) ───────────────────────────────────────────────────────

async def test_get_stats_uses_scan_and_returns_metrics():
    mock_redis = MagicMock()
    mock_redis.scan = AsyncMock(return_value=(0, [
        "rf:cache:analytics:sales:c1:2024-01-01:2024-03-01",
        "rf:cache:analytics:sales:c1:2024-01-01:2024-03-01:stale",
        "rf:cache:summary:c1",
        "rf:cache:insights:c1",
    ]))
    mock_redis.hgetall = AsyncMock(return_value={"hit": "50", "miss": "10", "stale_hit": "3"})
    mock_redis.ping = AsyncMock()
    mock_redis.info = AsyncMock(return_value={"used_memory_human": "2.5M", "connected_clients": 5})

    with patch("app.core.redis_client.get_redis", new_callable=AsyncMock) as mock_get_redis:
        mock_get_redis.return_value = mock_redis
        from app.core.cache import get_stats
        result = await get_stats()

    assert result["total_keys"] == 3  # stale keys excluded from count
    assert result["by_category"]["analytics"] == 1
    assert result["by_category"]["summary"] == 1
    assert result["by_category"]["insights"] == 1
    assert result["metrics"]["hits"] == 50
    assert result["metrics"]["hit_rate"] == round(50 / 63, 4)
    assert result["health"]["status"] == "healthy"


# ── Cache management endpoint tests ──────────────────────────────────────────

async def test_invalidate_all_analytics_cache():
    with patch("app.api.v1.endpoints.cache.delete_pattern", new_callable=AsyncMock) as mock_del:
        mock_del.return_value = 5
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.delete("/api/v1/cache/analytics")

    assert r.status_code == 200
    data = r.json()
    assert data["deleted"] == 20  # 4 patterns × 5 each
    assert data["dept"] is None
    assert data["warmed"] is None
    assert mock_del.call_count == 4


async def test_invalidate_dept_specific_cache():
    with patch("app.api.v1.endpoints.cache.delete_pattern", new_callable=AsyncMock) as mock_del:
        mock_del.return_value = 3
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.delete("/api/v1/cache/analytics?dept=sales")

    assert r.status_code == 200
    data = r.json()
    assert data["deleted"] == 3
    assert data["dept"] == "sales"
    mock_del.assert_called_once()


async def test_invalidate_cache_forbidden_for_sales():
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = _fake_sales
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.delete("/api/v1/cache/analytics")
        assert r.status_code == 403
    finally:
        app.dependency_overrides[get_current_user] = _fake_ceo


async def test_invalidate_unknown_dept_is_noop():
    with patch("app.api.v1.endpoints.cache.delete_pattern", new_callable=AsyncMock) as mock_del:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.delete("/api/v1/cache/analytics?dept=unknown_dept")

    assert r.status_code == 200
    assert r.json()["deleted"] == 0
    mock_del.assert_not_called()


async def test_warm_endpoint_calls_all_five_services():
    with patch("app.api.v1.endpoints.cache.warm_analytics_cache", new_callable=AsyncMock) as mock_warm:
        mock_warm.return_value = {
            "sales": True, "marketing": True, "operations": True,
            "finance": True, "procurement": True,
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/cache/warm")

    assert r.status_code == 200
    data = r.json()
    assert data["company_id"] == str(FAKE_CID)
    assert data["warmed"]["sales"] is True
    assert len(data["warmed"]) == 5


async def test_cache_health_endpoint():
    with patch("app.api.v1.endpoints.cache.health_check", new_callable=AsyncMock) as mock_health:
        mock_health.return_value = {
            "status": "healthy",
            "latency_ms": 1.23,
            "used_memory_human": "3.5M",
            "connected_clients": 2,
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/cache/health")

    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert data["latency_ms"] == 1.23
    assert data["used_memory_human"] == "3.5M"
