"""Notification endpoint tests — list, mark-read, mark-all-read."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.user import User, UserRole
from app.schemas.notification import NotificationListResponse, NotificationOut

FAKE_UID = uuid.uuid4()
FAKE_CID = uuid.uuid4()
FAKE_NID = uuid.uuid4()


def _fake_user() -> MagicMock:
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


@pytest.fixture(autouse=True)
def _override_auth():
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = _fake_user
    yield
    app.dependency_overrides.clear()


def _notif(read: bool = False) -> NotificationOut:
    return NotificationOut(
        id=FAKE_NID,
        type="warning",
        payload={"title": "Low stock warning", "message": "3 SKUs below reorder point"},
        read_at=datetime(2025, 2, 1, tzinfo=timezone.utc) if read else None,
        created_at=datetime(2025, 1, 31, tzinfo=timezone.utc),
    )


# ─── GET /notifications ──────────────────────────────────────────────────────

async def test_list_notifications_empty():
    """Empty list when no notifications exist."""
    empty = NotificationListResponse(items=[], unread_count=0)
    with patch(
        "app.api.v1.endpoints.notifications.list_notifications",
        new=AsyncMock(return_value=empty),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/notifications")

    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert data["unread_count"] == 0


async def test_list_notifications_with_data():
    """Returns notifications with correct unread count."""
    response = NotificationListResponse(
        items=[_notif(read=False), _notif(read=True)],
        unread_count=1,
    )
    with patch(
        "app.api.v1.endpoints.notifications.list_notifications",
        new=AsyncMock(return_value=response),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/notifications")

    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 2
    assert data["unread_count"] == 1
    assert data["items"][0]["type"] == "warning"


# ─── PATCH /notifications/{id}/read ─────────────────────────────────────────

async def test_mark_notification_read():
    """PATCH /{id}/read returns 204 when notification found."""
    with patch(
        "app.api.v1.endpoints.notifications.mark_read",
        new=AsyncMock(return_value=True),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.patch(f"/api/v1/notifications/{FAKE_NID}/read")

    assert r.status_code == 204


async def test_mark_notification_read_not_found():
    """PATCH /{id}/read returns 404 when notification not found."""
    with patch(
        "app.api.v1.endpoints.notifications.mark_read",
        new=AsyncMock(return_value=False),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.patch(f"/api/v1/notifications/{uuid.uuid4()}/read")

    assert r.status_code == 404


# ─── POST /notifications/read-all ────────────────────────────────────────────

async def test_mark_all_read():
    """POST /read-all returns 204."""
    with patch(
        "app.api.v1.endpoints.notifications.mark_all_read",
        new=AsyncMock(return_value=3),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/notifications/read-all")

    assert r.status_code == 204


# ─── Auth guard ─────────────────────────────────────────────────────────────

async def test_notifications_require_auth():
    """GET /notifications returns 403 without a bearer token."""
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/notifications")

    assert r.status_code == 403
