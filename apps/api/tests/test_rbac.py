"""RBAC matrix tests — verifies dept-level access control across all role × endpoint combinations."""
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.user import User, UserRole
from app.schemas.analytics import (
    DashboardSummaryOut,
    FinanceKpisOut,
    MarketingKpisOut,
    OperationsKpisOut,
    ProcurementKpisOut,
    SalesKpisOut,
)

FAKE_UID = uuid.uuid4()
FAKE_CID = uuid.uuid4()

ENDPOINTS = [
    "/api/v1/analytics/sales",
    "/api/v1/analytics/marketing",
    "/api/v1/analytics/operations",
    "/api/v1/analytics/finance",
    "/api/v1/analytics/procurement",
    "/api/v1/analytics/summary",
]

DEPT_MAP = {
    "/api/v1/analytics/sales": "sales",
    "/api/v1/analytics/marketing": "marketing",
    "/api/v1/analytics/operations": "operations",
    "/api/v1/analytics/finance": "finance",
    "/api/v1/analytics/procurement": "procurement",
    "/api/v1/analytics/summary": "summary",
}

ROLE_DEPT_ACCESS = {
    UserRole.CEO: {"sales", "marketing", "operations", "finance", "procurement", "summary"},
    UserRole.ADMIN: {"sales", "marketing", "operations", "finance", "procurement", "summary"},
    UserRole.SALES: {"sales", "summary"},
    UserRole.MARKETING: {"marketing", "summary"},
    UserRole.FINANCE: {"finance", "summary"},
    UserRole.OPERATIONS: {"operations", "summary"},
    UserRole.PROCUREMENT: {"procurement", "summary"},
}


def _make_user(role: UserRole) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = FAKE_UID
    u.email = f"{role.value}@acme.com"
    u.name = role.value.capitalize()
    u.role = role
    u.company_id = FAKE_CID
    u.is_active = True
    u.last_login_at = None
    u.prefs = None
    u.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return u


def _cursor(docs: list) -> MagicMock:
    c = MagicMock()
    c.to_list = AsyncMock(return_value=docs)
    return c


def _empty_mongo_db() -> MagicMock:
    col = MagicMock()
    col.aggregate = MagicMock(side_effect=lambda *a, **kw: _cursor([]))
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=col)
    return db


_EMPTY_SALES = SalesKpisOut(total_revenue=0, total_units=0, aov=0, top_sku=None,
                             top_skus=[], revenue_by_region=[], daily_revenue=[])
_EMPTY_MKT = MarketingKpisOut(total_spend=0, total_conversions=0, total_impressions=0,
                               ctr=0, roas=0, cac=0, top_campaigns=[], spend_by_campaign=[],
                               daily_spend=[])
_EMPTY_OPS = OperationsKpisOut(total_skus=0, total_stock_units=0, skus_below_reorder=0,
                                active_warehouses=0, stock_by_warehouse=[], low_stock_skus=[],
                                daily_stock_level=[])
_EMPTY_FIN = FinanceKpisOut(total_revenue=0, total_cogs=0, total_gross_profit=0,
                             gross_margin=0, revenue_by_category=[], daily_gross_profit=[],
                             monthly_pnl=[])
_EMPTY_PROC = ProcurementKpisOut(total_spend=0, total_units=0, unique_suppliers=0,
                                  avg_lead_days=0, top_suppliers=[], daily_spend=[],
                                  top_sku_costs=[])


@contextmanager
def _mock_services_for(endpoint: str):
    """Patch the right service(s) so the endpoint can return 200."""
    dept = DEPT_MAP[endpoint]
    if dept == "summary":
        with (
            patch("app.domains.analytics.summary_service.get_sales_kpis",
                  new=AsyncMock(return_value=_EMPTY_SALES)),
            patch("app.domains.analytics.summary_service.get_marketing_kpis",
                  new=AsyncMock(return_value=_EMPTY_MKT)),
            patch("app.domains.analytics.summary_service.get_operations_kpis",
                  new=AsyncMock(return_value=_EMPTY_OPS)),
            patch("app.domains.analytics.summary_service.get_finance_kpis",
                  new=AsyncMock(return_value=_EMPTY_FIN)),
            patch("app.domains.analytics.summary_service.get_procurement_kpis",
                  new=AsyncMock(return_value=_EMPTY_PROC)),
            patch("app.domains.analytics.summary_service.get_json",
                  new=AsyncMock(return_value=None)),
            patch("app.domains.analytics.summary_service.set_json",
                  new=AsyncMock()),
        ):
            yield
    else:
        mock_db = _empty_mongo_db()
        service_module = f"app.domains.analytics.{dept}_service"
        with (
            patch(f"{service_module}.get_mongo_db", return_value=mock_db),
            patch(f"{service_module}.get_json", new=AsyncMock(return_value=None)),
            patch(f"{service_module}.set_json", new=AsyncMock()),
        ):
            yield


async def _run_rbac_test(role: UserRole, endpoint: str):
    """Run a single RBAC assertion for role × endpoint."""
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: _make_user(role)

    dept = DEPT_MAP[endpoint]
    allowed = dept in ROLE_DEPT_ACCESS[role]

    with _mock_services_for(endpoint):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(endpoint)

    app.dependency_overrides.clear()
    if allowed:
        assert r.status_code == 200, f"{role.value} should access {dept}, got {r.status_code}"
    else:
        assert r.status_code == 403, f"{role.value} should NOT access {dept}, got {r.status_code}"


# ─── CEO can access everything ──────────────────────────────────────────────

@pytest.mark.parametrize("endpoint", ENDPOINTS)
async def test_ceo_can_access_all_endpoints(endpoint: str):
    await _run_rbac_test(UserRole.CEO, endpoint)


# ─── ADMIN can access everything ────────────────────────────────────────────

@pytest.mark.parametrize("endpoint", ENDPOINTS)
async def test_admin_can_access_all_endpoints(endpoint: str):
    await _run_rbac_test(UserRole.ADMIN, endpoint)


# ─── SALES role: sales + summary only ───────────────────────────────────────

@pytest.mark.parametrize("endpoint", ENDPOINTS)
async def test_sales_role_access(endpoint: str):
    await _run_rbac_test(UserRole.SALES, endpoint)


# ─── MARKETING role: marketing + summary only ────────────────────────────────

@pytest.mark.parametrize("endpoint", ENDPOINTS)
async def test_marketing_role_access(endpoint: str):
    await _run_rbac_test(UserRole.MARKETING, endpoint)


# ─── FINANCE role: finance + summary only ────────────────────────────────────

@pytest.mark.parametrize("endpoint", ENDPOINTS)
async def test_finance_role_access(endpoint: str):
    await _run_rbac_test(UserRole.FINANCE, endpoint)


# ─── OPERATIONS role: operations + summary only ──────────────────────────────

@pytest.mark.parametrize("endpoint", ENDPOINTS)
async def test_operations_role_access(endpoint: str):
    await _run_rbac_test(UserRole.OPERATIONS, endpoint)


# ─── PROCUREMENT role: procurement + summary only ────────────────────────────

@pytest.mark.parametrize("endpoint", ENDPOINTS)
async def test_procurement_role_access(endpoint: str):
    await _run_rbac_test(UserRole.PROCUREMENT, endpoint)
