"""Report export endpoint tests (analytics services mocked)."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.user import User, UserRole
from app.schemas.analytics import (
    DailyRevenue,
    DailySpend,
    DailyStockLevel,
    FinanceKpisOut,
    MarketingKpisOut,
    MonthlyPnL,
    OperationsKpisOut,
    ProcurementKpisOut,
    SalesKpisOut,
)

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


async def test_export_sales_csv():
    """CSV export for sales returns date + revenue rows."""
    fake_sales = SalesKpisOut(
        total_revenue=5000.0,
        total_units=50,
        aov=100.0,
        top_sku="BLZ-BLK-M",
        top_skus=[],
        revenue_by_region=[],
        daily_revenue=[
            DailyRevenue(date="2024-01-01", revenue=1000.0),
            DailyRevenue(date="2024-01-02", revenue=1500.0),
        ],
    )

    with patch(
        "app.domains.reports.report_service.get_sales_kpis",
        new=AsyncMock(return_value=fake_sales),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/reports/export?dept=sales&fmt=csv")

    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "attachment" in r.headers["content-disposition"]
    assert "date" in r.text
    assert "revenue" in r.text
    assert "2024-01-01" in r.text


async def test_export_finance_json():
    """JSON export for finance returns full KPI object."""
    fake_finance = FinanceKpisOut(
        total_revenue=12000.0,
        total_cogs=7200.0,
        total_gross_profit=4800.0,
        gross_margin=40.0,
        revenue_by_category=[],
        daily_gross_profit=[],
        monthly_pnl=[MonthlyPnL(month="2024-01", revenue=12000.0, cogs=7200.0)],
    )

    with patch(
        "app.domains.reports.report_service.get_finance_kpis",
        new=AsyncMock(return_value=fake_finance),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/reports/export?dept=finance&fmt=json")

    assert r.status_code == 200
    assert "application/json" in r.headers["content-type"]
    data = r.json()
    assert data["total_revenue"] == 12000.0
    assert data["gross_margin"] == 40.0


async def test_export_empty_csv():
    """CSV export returns empty bytes when no data is available."""
    fake_ops = OperationsKpisOut(
        total_skus=0,
        total_stock_units=0,
        skus_below_reorder=0,
        active_warehouses=0,
        stock_by_warehouse=[],
        low_stock_skus=[],
        daily_stock_level=[],
    )

    with patch(
        "app.domains.reports.report_service.get_operations_kpis",
        new=AsyncMock(return_value=fake_ops),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/reports/export?dept=operations&fmt=csv")

    assert r.status_code == 200
    assert r.content == b""


async def test_export_requires_auth():
    """Endpoint returns 403 when no bearer token is provided."""
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/reports/export?dept=sales&fmt=csv")

    app.dependency_overrides.clear()
    assert r.status_code == 403
