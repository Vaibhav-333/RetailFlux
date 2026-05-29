"""Alert preferences and check endpoint tests."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.user import User, UserRole
from app.schemas.alerts import AlertCheckResult

FAKE_UID = uuid.uuid4()
FAKE_CID = uuid.uuid4()


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


def _mongo_col(find_one_return=None):
    col = MagicMock()
    col.find_one = AsyncMock(return_value=find_one_return)
    col.update_one = AsyncMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[])
    col.find = MagicMock(return_value=cursor)
    return col


def _mock_mongo(col):
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=col)
    return db


# ─── GET /alerts/preferences ──────────────────────────────────────────────────

async def test_get_prefs_returns_defaults():
    """Returns default prefs when no document is stored for this user."""
    col = _mongo_col(find_one_return=None)
    with patch("app.domains.alerts.alert_service.get_mongo_db", return_value=_mock_mongo(col)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/alerts/preferences")

    assert r.status_code == 200
    data = r.json()
    assert data["email_alerts_enabled"] is True
    assert data["alert_on_anomalies"] is True
    assert data["alert_on_low_stock"] is True


async def test_get_prefs_returns_stored_values():
    """Returns stored prefs when a document exists for this user."""
    stored = {
        "user_id": str(FAKE_UID),
        "email_alerts_enabled": False,
        "alert_on_anomalies": True,
        "alert_on_low_stock": False,
    }
    col = _mongo_col(find_one_return=stored)
    with patch("app.domains.alerts.alert_service.get_mongo_db", return_value=_mock_mongo(col)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/alerts/preferences")

    assert r.status_code == 200
    data = r.json()
    assert data["email_alerts_enabled"] is False
    assert data["alert_on_low_stock"] is False


# ─── PATCH /alerts/preferences ────────────────────────────────────────────────

async def test_patch_prefs_updates_field():
    """PATCH updates specified fields and returns merged result."""
    updated_doc = {
        "user_id": str(FAKE_UID),
        "email_alerts_enabled": False,
        "alert_on_anomalies": True,
        "alert_on_low_stock": True,
    }
    col = MagicMock()
    col.update_one = AsyncMock()
    # find_one is called once after the update to return updated state
    col.find_one = AsyncMock(return_value=updated_doc)

    with patch("app.domains.alerts.alert_service.get_mongo_db", return_value=_mock_mongo(col)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.patch("/api/v1/alerts/preferences", json={"email_alerts_enabled": False})

    assert r.status_code == 200
    assert r.json()["email_alerts_enabled"] is False
    col.update_one.assert_awaited_once()


# ─── Auth guard ───────────────────────────────────────────────────────────────

async def test_prefs_requires_auth():
    """GET /alerts/preferences returns 403 without a bearer token."""
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/alerts/preferences")

    assert r.status_code == 403


# ─── POST /alerts/check ───────────────────────────────────────────────────────

async def test_check_requires_ceo():
    """Non-CEO role (SALES) gets 403 on POST /alerts/check."""
    from app.domains.auth.dependencies import get_current_user

    sales_user = _fake_user()
    sales_user.role = UserRole.SALES
    app.dependency_overrides[get_current_user] = lambda: sales_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/alerts/check")

    assert r.status_code == 403


async def test_check_returns_alert_result():
    """POST /alerts/check returns AlertCheckResult with correct shape."""
    result = AlertCheckResult(
        anomalies_found=2,
        low_stock_skus_found=3,
        emails_sent=5,
        notifications_created=5,
    )
    with patch(
        "app.api.v1.endpoints.alerts.check_and_send_alerts",
        new=AsyncMock(return_value=result),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/alerts/check")

    assert r.status_code == 200
    data = r.json()
    assert data["anomalies_found"] == 2
    assert data["low_stock_skus_found"] == 3
    assert data["emails_sent"] == 5
    assert data["notifications_created"] == 5


async def test_check_zero_result_when_no_data():
    """POST /alerts/check returns all-zero result when no anomalies or low stock."""
    result = AlertCheckResult(
        anomalies_found=0,
        low_stock_skus_found=0,
        emails_sent=0,
        notifications_created=0,
    )
    with patch(
        "app.api.v1.endpoints.alerts.check_and_send_alerts",
        new=AsyncMock(return_value=result),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/alerts/check")

    assert r.status_code == 200
    data = r.json()
    assert data["emails_sent"] == 0
    assert data["notifications_created"] == 0
