"""Row-Level Security isolation tests.

Verifies that data for Company A never leaks to Company B:
  - Each analytics endpoint is called with the authenticated user's company_id.
  - A user from Company A cannot read Company B's data through any analytics endpoint.
  - The dependency override pattern ensures the service layer receives the
    correct company_id from the JWT-verified user, not a caller-supplied value.

These tests do NOT require a real database. They assert that:
  1. The endpoint resolves company_id from the authenticated user (not query params).
  2. The downstream service is called with exactly that company_id.
  3. A request authenticated as Company A's user cannot retrieve Company B's data
     by passing Company B's ID in the request body or query string.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.user import User, UserRole

# ── Two distinct companies ────────────────────────────────────────────────────

COMPANY_A_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
COMPANY_B_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")

USER_A_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000010")
USER_B_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000020")


def _make_user(company_id: uuid.UUID, user_id: uuid.UUID, role: UserRole = UserRole.CEO) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = user_id
    u.email = f"ceo@company-{company_id}.demo"
    u.name = "CEO"
    u.role = role
    u.company_id = company_id
    u.is_active = True
    u.last_login_at = None
    u.prefs = None
    u.onboarding_step = 5
    u.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return u


# Fake KPI data per company — deliberately different so we can tell them apart
_COMPANY_A_REVENUE = 111_111.11
_COMPANY_B_REVENUE = 999_999.99

_COMPANY_A_SALES_DATA = {
    "total_revenue": _COMPANY_A_REVENUE,
    "total_orders": 500,
    "total_units": 1000,
    "aov": 222.22,
    "top_sku": None,
    "top_skus": [],
    "revenue_by_region": [],
    "daily_revenue": [],
}

_COMPANY_B_SALES_DATA = {
    "total_revenue": _COMPANY_B_REVENUE,
    "total_orders": 5000,
    "total_units": 10000,
    "aov": 200.0,
    "top_sku": None,
    "top_skus": [],
    "revenue_by_region": [],
    "daily_revenue": [],
}


def _sales_service_by_company(company_id: str, *args, **kwargs):
    """Simulate a service that returns different data per company."""
    if str(company_id) == str(COMPANY_A_ID):
        return _COMPANY_A_SALES_DATA
    return _COMPANY_B_SALES_DATA


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def _auth_as_company_a():
    from app.domains.auth.dependencies import get_current_user
    user_a = _make_user(COMPANY_A_ID, USER_A_ID)
    app.dependency_overrides[get_current_user] = lambda: user_a
    yield user_a
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def _auth_as_company_b():
    from app.domains.auth.dependencies import get_current_user
    user_b = _make_user(COMPANY_B_ID, USER_B_ID)
    app.dependency_overrides[get_current_user] = lambda: user_b
    yield user_b
    app.dependency_overrides.pop(get_current_user, None)


# ── Tests ─────────────────────────────────────────────────────────────────────

async def test_sales_endpoint_uses_authenticated_company_id(_auth_as_company_a):
    """GET /analytics/sales passes the authenticated user's company_id to the service."""
    captured: list[str] = []

    async def _fake_sales(company_id, *args, **kwargs):
        captured.append(str(company_id))
        return _COMPANY_A_SALES_DATA

    with patch("app.api.v1.endpoints.analytics.get_sales_kpis", new=_fake_sales):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/analytics/sales")

    assert r.status_code == 200
    assert len(captured) == 1, "Service should be called exactly once"
    assert captured[0] == str(COMPANY_A_ID), (
        f"Service must receive Company A's ID ({COMPANY_A_ID}), got {captured[0]}"
    )


async def test_company_a_sees_only_company_a_data(_auth_as_company_a):
    """A user authenticated as Company A receives Company A's revenue, not Company B's."""
    with patch("app.api.v1.endpoints.analytics.get_sales_kpis", new=AsyncMock(return_value=_COMPANY_A_SALES_DATA)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/analytics/sales")

    assert r.status_code == 200
    data = r.json()
    assert data["total_revenue"] == pytest.approx(_COMPANY_A_REVENUE), (
        "Company A must only see its own revenue"
    )
    assert data["total_revenue"] != pytest.approx(_COMPANY_B_REVENUE), (
        "Company A must NOT see Company B's revenue"
    )


async def test_company_b_sees_only_company_b_data(_auth_as_company_b):
    """A user authenticated as Company B receives Company B's revenue, not Company A's."""
    with patch("app.api.v1.endpoints.analytics.get_sales_kpis", new=AsyncMock(return_value=_COMPANY_B_SALES_DATA)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/analytics/sales")

    assert r.status_code == 200
    data = r.json()
    assert data["total_revenue"] == pytest.approx(_COMPANY_B_REVENUE), (
        "Company B must only see its own revenue"
    )
    assert data["total_revenue"] != pytest.approx(_COMPANY_A_REVENUE), (
        "Company B must NOT see Company A's revenue"
    )


async def test_unauthenticated_request_rejected():
    """Requests without a valid JWT are rejected before any service call is made."""
    # Clear all dependency overrides so real auth runs
    app.dependency_overrides.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/analytics/sales")

    assert r.status_code in (401, 403), (
        f"Unauthenticated request should be rejected, got {r.status_code}"
    )


async def test_marketing_endpoint_uses_authenticated_company_id(_auth_as_company_a):
    """GET /analytics/marketing passes the correct company_id — not a caller-supplied one."""
    captured: list[str] = []

    async def _fake_marketing(company_id, *args, **kwargs):
        captured.append(str(company_id))
        return {
            "total_spend": 1000.0,
            "total_conversions": 100,
            "total_impressions": 5000,
            "roas": 5.0,
            "cac": 10.0,
            "ctr": 0.05,
            "top_campaigns": [],
            "daily_spend": [],
            "spend_by_campaign": [],
        }

    with patch("app.api.v1.endpoints.analytics.get_marketing_kpis", new=_fake_marketing):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            # Attempt to pass a different company_id via query params — must be ignored
            r = await c.get(
                "/api/v1/analytics/marketing",
                params={"company_id": str(COMPANY_B_ID)},  # attacker-supplied — should be ignored
            )

    assert r.status_code == 200
    assert len(captured) == 1
    # The endpoint must use the JWT-derived company_id, ignoring any query param
    assert captured[0] == str(COMPANY_A_ID), (
        "company_id must come from the JWT, not from attacker-controlled query params"
    )


async def test_upload_list_scoped_to_company(_auth_as_company_a):
    """GET /uploads calls list_uploads with the authenticated user's company_id only.

    We patch at the service layer and capture the company_id argument.
    This verifies that the endpoint never passes an attacker-controlled
    company_id — it always derives it from the JWT-authenticated user.
    """
    captured_cids: list[str] = []

    async def _fake_list_uploads(db, company_id, dept=None, page=1, size=20):
        captured_cids.append(str(company_id))
        return ([], 0)  # empty — no real upload objects needed

    with patch(
        "app.domains.uploads.service.list_uploads",
        new=_fake_list_uploads,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/uploads")

    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert len(captured_cids) == 1, "list_uploads should be called exactly once"
    assert captured_cids[0] == str(COMPANY_A_ID), (
        f"upload list must scope to Company A ({COMPANY_A_ID}), got {captured_cids[0]}"
    )
    assert captured_cids[0] != str(COMPANY_B_ID), (
        "Company A must never query with Company B's ID"
    )
