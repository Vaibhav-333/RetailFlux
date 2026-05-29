"""Audit log endpoint tests."""
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
    u.onboarding_step = 0
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


async def test_audit_logs_empty():
    """Returns empty items list when no audit log entries exist."""
    from app.schemas.audit import AuditLogsResponse
    mock_svc = AsyncMock(return_value=AuditLogsResponse(items=[], total=0, page=1, pageSize=20))

    with patch("app.api.v1.endpoints.audit.list_audit_logs", mock_svc):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/audit/logs")

    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


async def test_audit_logs_with_data():
    """Returns audit entries with correct shape and values."""
    from app.schemas.audit import AuditLogEntry, AuditLogsResponse

    entry = AuditLogEntry(
        id=str(uuid.uuid4()),
        user_id=str(FAKE_UID),
        action="POST",
        resource="uploads",
        resource_id=None,
        ip="127.0.0.1",
        ua="pytest",
        created_at="2025-01-15T12:00:00+00:00",
    )
    mock_resp = AuditLogsResponse(items=[entry], total=1, page=1, pageSize=20)
    mock_svc = AsyncMock(return_value=mock_resp)

    with patch("app.api.v1.endpoints.audit.list_audit_logs", mock_svc):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/audit/logs")

    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["action"] == "POST"
    assert item["resource"] == "uploads"
    assert item["ip"] == "127.0.0.1"


async def test_audit_logs_pagination_params():
    """Pagination query params are forwarded to the service."""
    from app.schemas.audit import AuditLogsResponse
    mock_svc = AsyncMock(return_value=AuditLogsResponse(items=[], total=0, page=2, pageSize=10))

    with patch("app.api.v1.endpoints.audit.list_audit_logs", mock_svc):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/audit/logs?page=2&size=10&resource=uploads")

    assert r.status_code == 200
    call_kwargs = mock_svc.call_args.kwargs
    assert call_kwargs["page"] == 2
    assert call_kwargs["size"] == 10
    assert call_kwargs["resource"] == "uploads"


async def test_audit_logs_403_for_sales():
    """Sales role cannot access the audit log (CEO/Admin only)."""
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = _fake_sales
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/audit/logs")
        assert r.status_code == 403
    finally:
        app.dependency_overrides[get_current_user] = _fake_ceo
