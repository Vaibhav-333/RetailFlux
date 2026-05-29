"""User management endpoint tests (DB mocked, no real Postgres required)."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.domains.auth.dependencies import get_current_user
from app.main import app
from app.models.user import User, UserRole

ADMIN_ID = uuid.uuid4()
OTHER_ID = uuid.uuid4()
COMPANY_ID = uuid.uuid4()


def _fake_admin() -> MagicMock:
    u = MagicMock(spec=User)
    u.id = ADMIN_ID
    u.email = "admin@acme.com"
    u.name = "Admin"
    u.role = UserRole.CEO
    u.company_id = COMPANY_ID
    u.is_active = True
    u.last_login_at = None
    u.prefs = None
    u.onboarding_step = 0
    u.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return u


def _fake_other_user() -> MagicMock:
    u = MagicMock(spec=User)
    u.id = OTHER_ID
    u.email = "sales@acme.com"
    u.name = "Sales Rep"
    u.role = UserRole.SALES
    u.company_id = COMPANY_ID
    u.is_active = True
    u.last_login_at = None
    u.prefs = None
    u.onboarding_step = 0
    u.created_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
    return u


@pytest.fixture(autouse=True)
def _override_db():
    mock_session = AsyncMock()
    mock_session.add = MagicMock()  # add() is synchronous in SQLAlchemy

    async def _fake_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _fake_get_db
    yield mock_session
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token() -> str:
    return create_access_token(str(ADMIN_ID), extra={"company_id": str(COMPANY_ID)})


@pytest.fixture
def _with_admin():
    admin = _fake_admin()
    app.dependency_overrides[get_current_user] = lambda: admin
    yield admin
    app.dependency_overrides.pop(get_current_user, None)


async def test_list_users_returns_paginated_list(_override_db, _with_admin, admin_token):
    admin = _fake_admin()
    other = _fake_other_user()

    _override_db.scalar = AsyncMock(return_value=2)
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [admin, other]
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars_mock
    _override_db.execute = AsyncMock(return_value=execute_result)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["email"] == "admin@acme.com"


async def test_list_users_requires_admin(admin_token):
    sales_user = _fake_other_user()
    app.dependency_overrides[get_current_user] = lambda: sales_user
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(
                "/api/v1/users",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert r.status_code == 403


async def test_create_user_success(_override_db, _with_admin, admin_token):
    _override_db.scalar = AsyncMock(return_value=None)  # no conflict

    async def _mock_refresh(obj):
        # Simulate DB populating generated columns after insert
        obj.id = OTHER_ID
        obj.is_active = True
        obj.created_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
        obj.last_login_at = None
        obj.prefs = None
        obj.onboarding_step = 0

    _override_db.refresh = _mock_refresh

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "sales@acme.com",
                "password": "password123",
                "name": "Sales Rep",
                "role": "sales",
            },
        )

    assert r.status_code == 201
    assert r.json()["email"] == "sales@acme.com"
    assert r.json()["role"] == "sales"


async def test_update_user_role(_override_db, _with_admin, admin_token):
    target = _fake_other_user()
    _override_db.scalar = AsyncMock(return_value=target)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.patch(
            f"/api/v1/users/{OTHER_ID}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role": "marketing"},
        )

    assert r.status_code == 200
    assert target.role == "marketing"
    _override_db.commit.assert_awaited()


async def test_update_user_cannot_deactivate_self(_override_db, _with_admin, admin_token):
    _override_db.scalar = AsyncMock(return_value=_with_admin)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.patch(
            f"/api/v1/users/{ADMIN_ID}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_active": False},
        )

    assert r.status_code == 400
    assert "Cannot deactivate" in r.json()["detail"]
