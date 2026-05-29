"""Sales and marketing analytics endpoint tests (MongoDB mocked)."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

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


def _cursor(docs: list) -> MagicMock:
    c = MagicMock()
    c.to_list = AsyncMock(return_value=docs)
    return c


@pytest.fixture(autouse=True)
def _override_auth():
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = _fake_user
    yield
    app.dependency_overrides.clear()


async def test_sales_kpis_empty():
    """Returns zero-value KPIs when staging_sales has no matching documents."""
    col = MagicMock()
    col.aggregate = MagicMock(side_effect=lambda *a, **kw: _cursor([]))

    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)

    with patch("app.domains.analytics.sales_service.get_mongo_db", return_value=mock_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/analytics/sales")

    assert r.status_code == 200
    data = r.json()
    assert data["total_revenue"] == 0.0
    assert data["total_units"] == 0
    assert data["aov"] == 0.0
    assert data["top_sku"] is None
    assert data["top_skus"] == []
    assert data["revenue_by_region"] == []
    assert data["daily_revenue"] == []


async def test_sales_kpis_with_data():
    """Aggregated KPIs are returned correctly when data is present."""
    responses = [
        [{"_id": None, "total_revenue": 1500.0, "total_units": 10, "count": 5}],
        [{"_id": "BLZ-BLK-M", "revenue": 900.0}, {"_id": "SHT-WHT-L", "revenue": 600.0}],
        [{"_id": "North", "revenue": 1000.0}, {"_id": "South", "revenue": 500.0}],
        [{"_id": "2024-01-15", "revenue": 1500.0}],
    ]
    call_idx = 0

    def _side_effect(*args, **kwargs):
        nonlocal call_idx
        cursor = _cursor(responses[call_idx])
        call_idx += 1
        return cursor

    col = MagicMock()
    col.aggregate = MagicMock(side_effect=_side_effect)

    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)

    with patch("app.domains.analytics.sales_service.get_mongo_db", return_value=mock_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/analytics/sales?date_from=2024-01-01&date_to=2024-01-31")

    assert r.status_code == 200
    data = r.json()
    assert data["total_revenue"] == 1500.0
    assert data["total_units"] == 10
    assert data["aov"] == 300.0  # 1500 / 5
    assert data["top_sku"] == "BLZ-BLK-M"
    assert len(data["top_skus"]) == 2
    assert data["top_skus"][0] == {"sku": "BLZ-BLK-M", "revenue": 900.0}
    assert len(data["revenue_by_region"]) == 2
    assert data["revenue_by_region"][0] == {"region": "North", "revenue": 1000.0}
    assert data["daily_revenue"] == [{"date": "2024-01-15", "revenue": 1500.0}]


async def test_sales_analytics_requires_auth():
    """Endpoint returns 403 when no bearer token is provided."""
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/analytics/sales")

    app.dependency_overrides.clear()
    assert r.status_code == 403


# ─── Marketing analytics ──────────────────────────────────────────────────────

def _two_col_db(mkt_col: MagicMock, sales_col: MagicMock) -> MagicMock:
    """Return a mock DB whose __getitem__ routes to the right collection."""
    cols = {"staging_marketing": mkt_col, "staging_sales": sales_col}
    db = MagicMock()
    db.__getitem__ = MagicMock(side_effect=lambda k: cols[k])
    return db


async def test_marketing_kpis_empty():
    """Returns zero-value KPIs when both staging collections are empty."""
    empty_col = MagicMock()
    empty_col.aggregate = MagicMock(side_effect=lambda *a, **kw: _cursor([]))

    mock_db = _two_col_db(empty_col, empty_col)

    with patch("app.domains.analytics.marketing_service.get_mongo_db", return_value=mock_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/analytics/marketing")

    assert r.status_code == 200
    data = r.json()
    assert data["total_spend"] == 0.0
    assert data["total_conversions"] == 0
    assert data["total_impressions"] == 0
    assert data["ctr"] == 0.0
    assert data["roas"] == 0.0
    assert data["cac"] == 0.0
    assert data["top_campaigns"] == []
    assert data["spend_by_campaign"] == []
    assert data["daily_spend"] == []


async def test_marketing_kpis_with_data():
    """ROAS, CAC, and CTR are computed correctly when data is present."""
    mkt_responses = [
        [{"_id": None, "total_spend": 1000.0, "total_conversions": 50,
          "total_impressions": 20000, "total_clicks": 400}],
        [{"_id": "C01", "conversions": 30}, {"_id": "C02", "conversions": 20}],
        [{"_id": "2024-01-15", "spend": 1000.0}],
        [{"_id": "C01", "spend": 600.0}, {"_id": "C02", "spend": 400.0}],
    ]
    sales_responses = [
        [{"_id": None, "total_revenue": 5000.0}],
    ]

    mkt_idx = 0
    sales_idx = 0

    def _mkt_side(*a, **kw):
        nonlocal mkt_idx
        c = _cursor(mkt_responses[mkt_idx])
        mkt_idx += 1
        return c

    def _sales_side(*a, **kw):
        nonlocal sales_idx
        c = _cursor(sales_responses[sales_idx])
        sales_idx += 1
        return c

    mkt_col = MagicMock()
    mkt_col.aggregate = MagicMock(side_effect=_mkt_side)
    sales_col = MagicMock()
    sales_col.aggregate = MagicMock(side_effect=_sales_side)

    mock_db = _two_col_db(mkt_col, sales_col)

    with patch("app.domains.analytics.marketing_service.get_mongo_db", return_value=mock_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/analytics/marketing?date_from=2024-01-01&date_to=2024-01-31")

    assert r.status_code == 200
    data = r.json()
    assert data["total_spend"] == 1000.0
    assert data["total_conversions"] == 50
    assert data["total_impressions"] == 20000
    assert data["ctr"] == 2.0           # 400 / 20000 * 100
    assert data["roas"] == 5.0          # 5000 / 1000
    assert data["cac"] == 20.0          # 1000 / 50
    assert data["top_campaigns"][0] == {"campaign_id": "C01", "conversions": 30}
    assert len(data["top_campaigns"]) == 2
    assert data["daily_spend"] == [{"date": "2024-01-15", "spend": 1000.0}]
    assert data["spend_by_campaign"][0] == {"campaign_id": "C01", "spend": 600.0}


async def test_marketing_analytics_requires_auth():
    """Endpoint returns 403 when no bearer token is provided."""
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/analytics/marketing")

    app.dependency_overrides.clear()
    assert r.status_code == 403


# ─── Operations analytics ─────────────────────────────────────────────────────

async def test_operations_kpis_empty():
    """Returns zero-value KPIs when staging_operations has no matching documents."""
    col = MagicMock()
    col.aggregate = MagicMock(side_effect=lambda *a, **kw: _cursor([]))

    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)

    with patch("app.domains.analytics.operations_service.get_mongo_db", return_value=mock_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/analytics/operations")

    assert r.status_code == 200
    data = r.json()
    assert data["total_skus"] == 0
    assert data["total_stock_units"] == 0
    assert data["skus_below_reorder"] == 0
    assert data["active_warehouses"] == 0
    assert data["stock_by_warehouse"] == []
    assert data["low_stock_skus"] == []
    assert data["daily_stock_level"] == []


async def test_operations_kpis_with_data():
    """Inventory KPIs, warehouse stock, low-stock SKUs, and daily trend are returned correctly."""
    responses = [
        # totals pipeline
        [{"_id": None, "total_stock_units": 420, "total_skus": 5, "total_warehouses": 2}],
        # below-reorder pipeline  ($count returns {"total": N})
        [{"total": 2}],
        # stock by warehouse
        [{"_id": "WH-North", "stock_level": 260}, {"_id": "WH-South", "stock_level": 160}],
        # low-stock SKUs
        [
            {"_id": "BLZ-BLK-M", "avg_stock": 5.0, "reorder_point": 10},
            {"_id": "SHT-WHT-L", "avg_stock": 8.0, "reorder_point": 15},
        ],
        # daily avg stock
        [{"_id": "2024-01-15", "avg_stock_level": 84.0}],
    ]
    call_idx = 0

    def _side_effect(*args, **kwargs):
        nonlocal call_idx
        cursor = _cursor(responses[call_idx])
        call_idx += 1
        return cursor

    col = MagicMock()
    col.aggregate = MagicMock(side_effect=_side_effect)

    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)

    with patch("app.domains.analytics.operations_service.get_mongo_db", return_value=mock_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/analytics/operations?date_from=2024-01-01&date_to=2024-01-31")

    assert r.status_code == 200
    data = r.json()
    assert data["total_skus"] == 5
    assert data["total_stock_units"] == 420
    assert data["skus_below_reorder"] == 2
    assert data["active_warehouses"] == 2
    assert data["stock_by_warehouse"][0] == {"warehouse": "WH-North", "stock_level": 260}
    assert len(data["stock_by_warehouse"]) == 2
    assert data["low_stock_skus"][0] == {
        "sku": "BLZ-BLK-M", "stock_level": 5.0, "reorder_point": 10
    }
    assert data["daily_stock_level"] == [{"date": "2024-01-15", "avg_stock_level": 84.0}]


async def test_operations_analytics_requires_auth():
    """Endpoint returns 403 when no bearer token is provided."""
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/analytics/operations")

    app.dependency_overrides.clear()
    assert r.status_code == 403


# ─── Finance analytics ────────────────────────────────────────────────────────

async def test_finance_kpis_empty():
    """Returns zero-value KPIs when staging_finance has no matching documents."""
    col = MagicMock()
    col.aggregate = MagicMock(side_effect=lambda *a, **kw: _cursor([]))

    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)

    with patch("app.domains.analytics.finance_service.get_mongo_db", return_value=mock_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/analytics/finance")

    assert r.status_code == 200
    data = r.json()
    assert data["total_revenue"] == 0.0
    assert data["total_cogs"] == 0.0
    assert data["total_gross_profit"] == 0.0
    assert data["gross_margin"] == 0.0
    assert data["revenue_by_category"] == []
    assert data["daily_gross_profit"] == []
    assert data["monthly_pnl"] == []


async def test_finance_kpis_with_data():
    """Gross margin % is computed correctly and all list shapes are returned."""
    responses = [
        # totals
        [{"_id": None, "total_revenue": 12000.0, "total_cogs": 7200.0,
          "total_gross_profit": 4800.0}],
        # revenue by category
        [{"_id": "Outerwear", "revenue": 8000.0}, {"_id": "Footwear", "revenue": 4000.0}],
        # daily gross profit
        [{"_id": "2024-01-15", "gross_profit": 4800.0}],
        # monthly pnl
        [{"_id": "2024-01", "revenue": 12000.0, "cogs": 7200.0}],
    ]
    call_idx = 0

    def _side_effect(*args, **kwargs):
        nonlocal call_idx
        cursor = _cursor(responses[call_idx])
        call_idx += 1
        return cursor

    col = MagicMock()
    col.aggregate = MagicMock(side_effect=_side_effect)

    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)

    with patch("app.domains.analytics.finance_service.get_mongo_db", return_value=mock_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/analytics/finance?date_from=2024-01-01&date_to=2024-01-31")

    assert r.status_code == 200
    data = r.json()
    assert data["total_revenue"] == 12000.0
    assert data["total_cogs"] == 7200.0
    assert data["total_gross_profit"] == 4800.0
    assert data["gross_margin"] == 40.0          # 4800 / 12000 * 100
    assert data["revenue_by_category"][0] == {"category": "Outerwear", "revenue": 8000.0}
    assert len(data["revenue_by_category"]) == 2
    assert data["daily_gross_profit"] == [{"date": "2024-01-15", "gross_profit": 4800.0}]
    assert data["monthly_pnl"] == [{"month": "2024-01", "revenue": 12000.0, "cogs": 7200.0}]


async def test_finance_analytics_requires_auth():
    """Endpoint returns 403 when no bearer token is provided."""
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/analytics/finance")

    app.dependency_overrides.clear()
    assert r.status_code == 403


# ─── Dashboard summary ────────────────────────────────────────────────────────

async def test_summary_kpis_all_empty():
    """Returns zero-value summary when all dept collections are empty."""
    from app.schemas.analytics import (
        SalesKpisOut, MarketingKpisOut, OperationsKpisOut, FinanceKpisOut, ProcurementKpisOut,
    )

    empty_sales = SalesKpisOut(total_revenue=0, total_units=0, aov=0, top_sku=None,
                               top_skus=[], revenue_by_region=[], daily_revenue=[])
    empty_mkt = MarketingKpisOut(total_spend=0, total_conversions=0, total_impressions=0,
                                 ctr=0, roas=0, cac=0, top_campaigns=[], spend_by_campaign=[],
                                 daily_spend=[])
    empty_ops = OperationsKpisOut(total_skus=0, total_stock_units=0, skus_below_reorder=0,
                                  active_warehouses=0, stock_by_warehouse=[], low_stock_skus=[],
                                  daily_stock_level=[])
    empty_fin = FinanceKpisOut(total_revenue=0, total_cogs=0, total_gross_profit=0,
                               gross_margin=0, revenue_by_category=[], daily_gross_profit=[],
                               monthly_pnl=[])
    empty_proc = ProcurementKpisOut(total_spend=0, total_units=0, unique_suppliers=0,
                                    avg_lead_days=0, top_suppliers=[], daily_spend=[],
                                    top_sku_costs=[])

    with (
        patch("app.domains.analytics.summary_service.get_sales_kpis",
              new=AsyncMock(return_value=empty_sales)),
        patch("app.domains.analytics.summary_service.get_marketing_kpis",
              new=AsyncMock(return_value=empty_mkt)),
        patch("app.domains.analytics.summary_service.get_operations_kpis",
              new=AsyncMock(return_value=empty_ops)),
        patch("app.domains.analytics.summary_service.get_finance_kpis",
              new=AsyncMock(return_value=empty_fin)),
        patch("app.domains.analytics.summary_service.get_procurement_kpis",
              new=AsyncMock(return_value=empty_proc)),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/analytics/summary")

    assert r.status_code == 200
    data = r.json()
    assert data["total_revenue"] == 0.0
    assert data["roas"] == 0.0
    assert data["skus_below_reorder"] == 0
    assert data["gross_margin"] == 0.0
    assert data["procurement_spend"] == 0.0
    assert data["daily_revenue"] == []


async def test_summary_kpis_with_data():
    """Headline KPIs from all 5 departments are aggregated into the summary."""
    from app.schemas.analytics import (
        DailyRevenue, SalesKpisOut, MarketingKpisOut, OperationsKpisOut,
        FinanceKpisOut, ProcurementKpisOut,
    )

    sales_data = SalesKpisOut(
        total_revenue=50000.0, total_units=500, aov=100.0, top_sku="BLZ-BLK-M",
        top_skus=[], revenue_by_region=[],
        daily_revenue=[DailyRevenue(date="2024-01-15", revenue=50000.0)],
    )
    mkt_data = MarketingKpisOut(
        total_spend=10000.0, total_conversions=200, total_impressions=40000,
        ctr=0.5, roas=5.0, cac=50.0, top_campaigns=[], spend_by_campaign=[], daily_spend=[],
    )
    ops_data = OperationsKpisOut(
        total_skus=100, total_stock_units=5000, skus_below_reorder=3, active_warehouses=4,
        stock_by_warehouse=[], low_stock_skus=[], daily_stock_level=[],
    )
    fin_data = FinanceKpisOut(
        total_revenue=50000.0, total_cogs=30000.0, total_gross_profit=20000.0,
        gross_margin=40.0, revenue_by_category=[], daily_gross_profit=[], monthly_pnl=[],
    )
    proc_data = ProcurementKpisOut(
        total_spend=15000.0, total_units=300, unique_suppliers=8, avg_lead_days=6.5,
        top_suppliers=[], daily_spend=[], top_sku_costs=[],
    )

    with (
        patch("app.domains.analytics.summary_service.get_sales_kpis",
              new=AsyncMock(return_value=sales_data)),
        patch("app.domains.analytics.summary_service.get_marketing_kpis",
              new=AsyncMock(return_value=mkt_data)),
        patch("app.domains.analytics.summary_service.get_operations_kpis",
              new=AsyncMock(return_value=ops_data)),
        patch("app.domains.analytics.summary_service.get_finance_kpis",
              new=AsyncMock(return_value=fin_data)),
        patch("app.domains.analytics.summary_service.get_procurement_kpis",
              new=AsyncMock(return_value=proc_data)),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/analytics/summary")

    assert r.status_code == 200
    data = r.json()
    assert data["total_revenue"] == 50000.0
    assert data["top_sku"] == "BLZ-BLK-M"
    assert data["roas"] == 5.0
    assert data["marketing_spend"] == 10000.0
    assert data["skus_below_reorder"] == 3
    assert data["active_warehouses"] == 4
    assert data["gross_margin"] == 40.0
    assert data["total_gross_profit"] == 20000.0
    assert data["procurement_spend"] == 15000.0
    assert data["unique_suppliers"] == 8
    assert data["avg_lead_days"] == 6.5
    assert data["daily_revenue"] == [{"date": "2024-01-15", "revenue": 50000.0}]


async def test_summary_requires_auth():
    """Endpoint returns 403 when no bearer token is provided."""
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/analytics/summary")

    app.dependency_overrides.clear()
    assert r.status_code == 403


# ─── Procurement analytics ────────────────────────────────────────────────────

async def test_procurement_kpis_empty():
    """Returns zero-value KPIs when staging_procurement has no matching documents."""
    col = MagicMock()
    col.aggregate = MagicMock(side_effect=lambda *a, **kw: _cursor([]))

    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)

    with patch("app.domains.analytics.procurement_service.get_mongo_db", return_value=mock_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/analytics/procurement")

    assert r.status_code == 200
    data = r.json()
    assert data["total_spend"] == 0.0
    assert data["total_units"] == 0
    assert data["unique_suppliers"] == 0
    assert data["avg_lead_days"] == 0.0
    assert data["top_suppliers"] == []
    assert data["daily_spend"] == []
    assert data["top_sku_costs"] == []


async def test_procurement_kpis_with_data():
    """Supplier spend, daily trend, and SKU costs are returned correctly."""
    responses = [
        # totals (unique_suppliers already resolved to int by $addFields)
        [{"_id": None, "total_spend": 2250.0, "total_units": 50,
          "unique_suppliers": 2, "avg_lead_days": 7.5}],
        # top suppliers by spend
        [{"_id": "SUP-01", "spend": 1500.0}, {"_id": "SUP-02", "spend": 750.0}],
        # daily spend
        [{"_id": "2024-01-15", "spend": 2250.0}],
        # top SKU costs
        [{"_id": "BLZ-BLK-M", "avg_unit_cost": 45.0}, {"_id": "SHT-WHT-L", "avg_unit_cost": 30.0}],
    ]
    call_idx = 0

    def _side_effect(*args, **kwargs):
        nonlocal call_idx
        cursor = _cursor(responses[call_idx])
        call_idx += 1
        return cursor

    col = MagicMock()
    col.aggregate = MagicMock(side_effect=_side_effect)

    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)

    with patch("app.domains.analytics.procurement_service.get_mongo_db", return_value=mock_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/analytics/procurement?date_from=2024-01-01&date_to=2024-01-31")

    assert r.status_code == 200
    data = r.json()
    assert data["total_spend"] == 2250.0
    assert data["total_units"] == 50
    assert data["unique_suppliers"] == 2
    assert data["avg_lead_days"] == 7.5
    assert data["top_suppliers"][0] == {"supplier_id": "SUP-01", "spend": 1500.0}
    assert len(data["top_suppliers"]) == 2
    assert data["daily_spend"] == [{"date": "2024-01-15", "spend": 2250.0}]
    assert data["top_sku_costs"][0] == {"sku": "BLZ-BLK-M", "avg_unit_cost": 45.0}
    assert len(data["top_sku_costs"]) == 2


async def test_procurement_analytics_requires_auth():
    """Endpoint returns 403 when no bearer token is provided."""
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/analytics/procurement")

    app.dependency_overrides.clear()
    assert r.status_code == 403


# ─── compare_to delta tests ───────────────────────────────────────────────────

async def test_sales_compare_to_previous_period_returns_deltas():
    """When compare_to=previous_period, the response includes a non-null deltas dict."""
    # 4 aggregations for current period + 1 for compare period
    responses = [
        [{"_id": None, "total_revenue": 2000.0, "total_units": 20, "count": 10}],
        [{"_id": "SKU-A", "revenue": 2000.0}],
        [{"_id": "North", "revenue": 2000.0}],
        [{"_id": "2024-02-15", "revenue": 2000.0}],
        # prev period totals
        [{"_id": None, "total_revenue": 1000.0, "total_units": 10, "count": 5}],
    ]
    call_idx = 0

    def _side_effect(*args, **kwargs):
        nonlocal call_idx
        cursor = _cursor(responses[call_idx])
        call_idx += 1
        return cursor

    col = MagicMock()
    col.aggregate = MagicMock(side_effect=_side_effect)
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)

    with patch("app.domains.analytics.sales_service.get_mongo_db", return_value=mock_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(
                "/api/v1/analytics/sales"
                "?date_from=2024-02-01&date_to=2024-02-29&compare_to=previous_period"
            )

    assert r.status_code == 200
    data = r.json()
    assert data["total_revenue"] == 2000.0
    assert "deltas" in data
    assert data["deltas"] is not None
    # 2000 vs 1000 → +100%
    assert data["deltas"]["total_revenue"] == 100.0


async def test_sales_no_compare_to_deltas_is_none():
    """Without compare_to, deltas is null/None in the response."""
    responses = [
        [{"_id": None, "total_revenue": 1500.0, "total_units": 10, "count": 5}],
        [{"_id": "SKU-A", "revenue": 1500.0}],
        [{"_id": "North", "revenue": 1500.0}],
        [{"_id": "2024-01-15", "revenue": 1500.0}],
    ]
    call_idx = 0

    def _side_effect(*args, **kwargs):
        nonlocal call_idx
        cursor = _cursor(responses[call_idx])
        call_idx += 1
        return cursor

    col = MagicMock()
    col.aggregate = MagicMock(side_effect=_side_effect)
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)

    with patch("app.domains.analytics.sales_service.get_mongo_db", return_value=mock_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/analytics/sales?date_from=2024-01-01&date_to=2024-01-31")

    assert r.status_code == 200
    data = r.json()
    assert data.get("deltas") is None


async def test_utils_compute_compare_period_previous_period():
    """compute_compare_period correctly shifts window for previous_period."""
    from app.domains.analytics.utils import compute_compare_period
    result = compute_compare_period("2024-02-01", "2024-02-29", "previous_period")
    assert result is not None
    prev_from, prev_to = result
    # 29 days → prev window ends 2024-01-31, starts 2024-01-03
    assert prev_to == "2024-01-31"
    assert prev_from == "2024-01-03"


async def test_utils_compute_compare_period_previous_year():
    """compute_compare_period correctly shifts window 365 days for previous_year."""
    from app.domains.analytics.utils import compute_compare_period
    # Non-leap-year window: 2024-01-01 → 2024-01-31 shifted 365 days back
    result = compute_compare_period("2024-01-01", "2024-01-31", "previous_year")
    assert result is not None
    prev_from, prev_to = result
    assert prev_from == "2023-01-01"
    assert prev_to == "2023-01-31"


async def test_utils_pct_delta():
    """pct_delta returns correct values including None for zero prev."""
    from app.domains.analytics.utils import pct_delta
    assert pct_delta(110.0, 100.0) == 10.0
    assert pct_delta(90.0, 100.0) == -10.0
    assert pct_delta(0.0, 0.0) is None
    assert pct_delta(50.0, 0.0) is None


async def test_utils_parse_dims():
    """parse_dims correctly converts key=val pairs."""
    from app.domains.analytics.utils import parse_dims
    result = parse_dims("region=North,channel=online")
    assert result == {"region": "North", "channel": "online"}
    assert parse_dims(None) == {}
    assert parse_dims("") == {}
