"""Auth system integration tests (service layer mocked; no real DB required)."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token
from app.main import app
from app.models.user import User, UserRole

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
def _override_db():
    mock_session = AsyncMock()

    async def _fake_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _fake_get_db
    yield mock_session
    app.dependency_overrides.clear()


async def test_register_success():
    user = _fake_user()
    access_tok = create_access_token(str(FAKE_UID), extra={"company_id": str(FAKE_CID)})
    refresh_tok, _ = create_refresh_token(str(FAKE_UID), extra={"company_id": str(FAKE_CID)})

    with patch("app.domains.auth.service.register", new_callable=AsyncMock) as mock_reg:
        mock_reg.return_value = (user, access_tok, refresh_tok)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/auth/register",
                json={
                    "company_name": "ACME Corp",
                    "email": "ceo@acme.com",
                    "password": "password123",
                    "name": "CEO",
                },
            )

    assert r.status_code == 201
    data = r.json()
    assert data["access_token"] == access_tok
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "ceo@acme.com"
    assert data["user"]["role"] == "ceo"
    mock_reg.assert_awaited_once()


async def test_register_validation_rejects_short_password():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/api/v1/auth/register",
            json={
                "company_name": "ACME",
                "email": "ceo@acme.com",
                "password": "short",
                "name": "CEO",
            },
        )
    assert r.status_code == 422


async def test_login_returns_token():
    user = _fake_user()
    access_tok = create_access_token(str(FAKE_UID), extra={"company_id": str(FAKE_CID)})
    refresh_tok, _ = create_refresh_token(str(FAKE_UID), extra={"company_id": str(FAKE_CID)})

    with patch("app.domains.auth.service.login", new_callable=AsyncMock) as mock_login:
        mock_login.return_value = (user, access_tok, refresh_tok)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/auth/login",
                json={"email": "ceo@acme.com", "password": "password123"},
            )

    assert r.status_code == 200
    assert r.json()["access_token"] == access_tok
    assert "refresh_token" in r.cookies


async def test_login_bad_credentials_returns_401():
    with patch("app.domains.auth.service.login", new_callable=AsyncMock) as mock_login:
        from fastapi import HTTPException, status as s
        mock_login.side_effect = HTTPException(
            status_code=s.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/auth/login",
                json={"email": "wrong@example.com", "password": "wrong"},
            )
    assert r.status_code == 401


async def test_refresh_without_cookie_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/auth/refresh")
    assert r.status_code == 401


async def test_logout_clears_cookie():
    refresh_tok, _ = create_refresh_token(str(FAKE_UID), extra={"company_id": str(FAKE_CID)})

    with patch("app.domains.auth.service.logout", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            c.cookies.set("refresh_token", refresh_tok, path="/api/v1/auth")
            r = await c.post("/api/v1/auth/logout")
    assert r.status_code == 204


async def test_protected_endpoint_without_token_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/users/me")
    assert r.status_code == 403


async def test_get_me_with_valid_token():
    from app.domains.auth.dependencies import get_current_user
    user = _fake_user()
    access_tok = create_access_token(str(FAKE_UID), extra={"company_id": str(FAKE_CID)})

    async def _fake_current_user() -> MagicMock:
        return user

    app.dependency_overrides[get_current_user] = _fake_current_user
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {access_tok}"},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert r.status_code == 200
    assert r.json()["email"] == "ceo@acme.com"
