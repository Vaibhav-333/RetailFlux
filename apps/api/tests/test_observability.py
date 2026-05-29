"""Observability dashboard endpoint tests."""
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


def _cursor(docs: list) -> MagicMock:
    c = MagicMock()
    c.to_list = AsyncMock(return_value=docs)
    return c


def _find_cursor(docs: list) -> MagicMock:
    c = MagicMock()
    c.sort = MagicMock(return_value=c)
    c.skip = MagicMock(return_value=c)
    c.limit = MagicMock(return_value=c)
    c.to_list = AsyncMock(return_value=docs)
    return c


@pytest.fixture(autouse=True)
def _override_auth():
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = _fake_ceo
    yield
    app.dependency_overrides.clear()


async def test_dashboard_empty():
    """Returns zero values when no metrics documents exist."""
    col = MagicMock()
    col.aggregate = MagicMock(side_effect=lambda *a, **kw: _cursor([]))
    col.find = MagicMock(return_value=_find_cursor([]))

    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)

    with patch("app.domains.observability.service.get_mongo_db", return_value=mock_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/observability/dashboard")

    assert r.status_code == 200
    data = r.json()
    assert data["total_requests_24h"] == 0
    assert data["error_count_24h"] == 0
    assert data["error_rate_24h"] == 0.0
    assert data["avg_duration_ms_24h"] == 0.0
    assert data["p95_duration_ms_24h"] == 0.0
    assert data["hourly_volume"] == []
    assert data["top_endpoints"] == []


async def test_dashboard_with_data():
    """Correctly computes error rate, P95, and shapes from aggregation results."""
    summary = [{"total": 500, "errors": 25, "avg_duration": 120.5}]
    hourly = [
        {"_id": "2025-01-15T14:00:00", "requests": 200, "errors": 10},
        {"_id": "2025-01-15T15:00:00", "requests": 300, "errors": 15},
    ]
    endpoints = [
        {
            "_id": {"endpoint": "/api/v1/analytics/sales", "method": "GET"},
            "request_count": 200,
            "avg_duration_ms": 95.0,
            "error_count": 5,
        }
    ]
    col = MagicMock()
    col.aggregate = MagicMock(
        side_effect=[_cursor(summary), _cursor(hourly), _cursor(endpoints)]
    )
    col.find = MagicMock(return_value=_find_cursor([{"duration_ms": 310.0}]))

    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)

    with patch("app.domains.observability.service.get_mongo_db", return_value=mock_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/observability/dashboard")

    assert r.status_code == 200
    data = r.json()
    assert data["total_requests_24h"] == 500
    assert data["error_count_24h"] == 25
    assert data["error_rate_24h"] == pytest.approx(0.05, abs=1e-4)
    assert data["avg_duration_ms_24h"] == pytest.approx(120.5)
    assert data["p95_duration_ms_24h"] == pytest.approx(310.0)
    assert len(data["hourly_volume"]) == 2
    assert data["hourly_volume"][0]["hour"] == "2025-01-15T14:00:00"
    assert data["hourly_volume"][0]["requests"] == 200
    assert len(data["top_endpoints"]) == 1
    ep = data["top_endpoints"][0]
    assert ep["endpoint"] == "/api/v1/analytics/sales"
    assert ep["request_count"] == 200
    assert ep["error_rate"] == pytest.approx(0.025, abs=1e-4)


async def test_dashboard_error_rate_zero_when_no_errors():
    """Error rate stays 0.0 when all requests are successful."""
    summary = [{"total": 100, "errors": 0, "avg_duration": 80.0}]
    col = MagicMock()
    col.aggregate = MagicMock(
        side_effect=[_cursor(summary), _cursor([]), _cursor([])]
    )
    col.find = MagicMock(return_value=_find_cursor([{"duration_ms": 90.0}]))

    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)

    with patch("app.domains.observability.service.get_mongo_db", return_value=mock_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/observability/dashboard")

    assert r.status_code == 200
    assert r.json()["error_rate_24h"] == 0.0
    assert r.json()["total_requests_24h"] == 100


async def test_dashboard_auth_required_for_sales():
    """SALES role is blocked with 403 (CEO/Admin only endpoint)."""
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = _fake_sales
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/observability/dashboard")
        assert r.status_code == 403
    finally:
        app.dependency_overrides[get_current_user] = _fake_ceo


# ── Celery stats ───────────────────────────────────────────────────────────────

async def test_celery_stats_empty():
    """Returns zero values when celery_metrics collection is empty."""
    col = MagicMock()
    col.aggregate = MagicMock(side_effect=lambda *a, **kw: _cursor([]))

    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)

    with patch("app.domains.observability.service.get_mongo_db", return_value=mock_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/observability/celery-stats")

    assert r.status_code == 200
    data = r.json()
    assert data["total_tasks_24h"] == 0
    assert data["success_rate_24h"] == 0.0
    assert data["by_task"] == []
    assert data["recent_failures"] == []


async def test_celery_stats_with_data():
    """Correctly computes success rate and per-task breakdown."""
    summary = [{"total": 50, "success": 48, "failure": 2, "avg_duration": 2100.0}]
    by_task = [
        {"_id": "periodic_alert_check", "total": 24, "success": 24, "failure": 0, "avg_duration": 1800.0},
        {"_id": "process_upload", "total": 26, "success": 24, "failure": 2, "avg_duration": 2350.0},
    ]
    failures = [
        {"task_name": "process_upload", "error": "File not found", "timestamp": datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)},
    ]
    col = MagicMock()
    col.aggregate = MagicMock(
        side_effect=[_cursor(summary), _cursor(by_task), _cursor(failures)]
    )

    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)

    with patch("app.domains.observability.service.get_mongo_db", return_value=mock_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/observability/celery-stats")

    assert r.status_code == 200
    data = r.json()
    assert data["total_tasks_24h"] == 50
    assert data["success_count_24h"] == 48
    assert data["failure_count_24h"] == 2
    assert data["success_rate_24h"] == pytest.approx(0.96, abs=1e-4)
    assert data["avg_duration_ms_24h"] == pytest.approx(2100.0)
    assert len(data["by_task"]) == 2
    assert data["by_task"][0]["task_name"] == "periodic_alert_check"
    assert data["by_task"][0]["success_rate"] == 1.0
    assert len(data["recent_failures"]) == 1
    assert data["recent_failures"][0]["error"] == "File not found"
