"""Inventory intelligence tests: pure algorithm unit tests + endpoint tests."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.domains.inventory.abc_xyz_service import classify_abc, classify_xyz
from app.domains.inventory.aging_service import classify_aging_bucket, compute_doh
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


def _seq_col(*response_lists: list) -> MagicMock:
    """Collection mock whose aggregate() cycles through response_lists."""
    idx = [0]

    def _side(*args, **kwargs):
        result = _cursor(response_lists[idx[0] % len(response_lists)])
        idx[0] += 1
        return result

    col = MagicMock()
    col.aggregate = MagicMock(side_effect=_side)
    return col


def _multi_db(**col_map: MagicMock) -> MagicMock:
    """Mock MongoDB whose __getitem__ routes to named collection mocks."""
    empty_col = MagicMock()
    empty_col.aggregate = MagicMock(return_value=_cursor([]))
    db = MagicMock()
    db.__getitem__ = MagicMock(side_effect=lambda k: col_map.get(k, empty_col))
    return db


@pytest.fixture(autouse=True)
def _override_auth():
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = _fake_user
    yield
    app.dependency_overrides.clear()


# ── Pure function tests ───────────────────────────────────────────────────────


def test_classify_abc_golden():
    """A=top80% by revenue, B=next15%, C=rest."""
    revenues = [
        ("SKU-A", 800.0),
        ("SKU-B", 100.0),
        ("SKU-C", 60.0),
        ("SKU-D", 40.0),
    ]
    result = classify_abc(revenues)
    assert result["SKU-A"] == "A"
    assert result["SKU-B"] == "B"
    assert result["SKU-C"] == "C"
    assert result["SKU-D"] == "C"


def test_classify_abc_empty():
    assert classify_abc([]) == {}


def test_classify_abc_zero_revenue():
    result = classify_abc([("SKU-A", 0.0), ("SKU-B", 0.0)])
    assert all(v == "C" for v in result.values())


def test_classify_xyz_golden():
    """X=CV<0.25, Y=CV<0.50, Z=CV≥0.50."""
    # X: uniform demand → low CV
    demands_x = {"SKU-X": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0]}
    result_x = classify_xyz(demands_x)
    assert result_x["SKU-X"] == "X"

    # Z: highly variable demand
    demands_z = {"SKU-Z": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 500.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}
    result_z = classify_xyz(demands_z)
    assert result_z["SKU-Z"] == "Z"


def test_classify_xyz_zero_demand():
    result = classify_xyz({"SKU": [0.0, 0.0, 0.0]})
    assert result["SKU"] == "Z"


def test_classify_xyz_insufficient_weeks():
    result = classify_xyz({"SKU": [50.0]})
    assert result["SKU"] == "Z"


def test_compute_doh_happy():
    assert compute_doh(100.0, 10.0) == 10.0


def test_compute_doh_zero_demand():
    assert compute_doh(100.0, 0.0) is None


def test_classify_aging_bucket():
    assert classify_aging_bucket(None) == "180+d"
    assert classify_aging_bucket(15.0) == "<30d"
    assert classify_aging_bucket(45.0) == "30-60d"
    assert classify_aging_bucket(75.0) == "60-90d"
    assert classify_aging_bucket(120.0) == "90-180d"
    assert classify_aging_bucket(200.0) == "180+d"


# ── Endpoint tests ────────────────────────────────────────────────────────────


async def test_inventory_overview_empty():
    """Returns zero KPIs when no operations data."""
    col = MagicMock()
    col.aggregate = MagicMock(return_value=_cursor([]))
    db = _multi_db(staging_operations=col)

    with patch("app.domains.inventory.service.get_mongo_db", return_value=db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/inventory/overview")

    assert r.status_code == 200
    data = r.json()
    assert data["total_skus"] == 0
    assert data["total_inventory_value"] == 0.0
    assert data["avg_health_score"] == 0.0


async def test_inventory_overview_with_data():
    """KPI aggregation computes correctly with mock data."""
    ops_col = _seq_col(
        # Call 1: latest date
        [{"_id": None, "max_date": "2024-01-31"}],
        # Call 2: stock on that date
        [{"_id": "SKU-A", "total_stock": 100.0, "reorder_point": 50.0},
         {"_id": "SKU-B", "total_stock": 20.0, "reorder_point": 30.0}],
    )
    sales_col = _seq_col(
        [{"_id": "SKU-A", "total_qty": 280.0}, {"_id": "SKU-B", "total_qty": 28.0}],
    )
    proc_col = _seq_col(
        [{"_id": "SKU-A", "avg_cost": 10.0}, {"_id": "SKU-B", "avg_cost": 20.0}],
    )
    db = _multi_db(
        staging_operations=ops_col,
        staging_sales=sales_col,
        staging_procurement=proc_col,
    )

    with patch("app.domains.inventory.service.get_mongo_db", return_value=db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/inventory/overview")

    assert r.status_code == 200
    data = r.json()
    assert data["total_skus"] == 2
    assert data["total_inventory_value"] == pytest.approx(100.0 * 10.0 + 20.0 * 20.0)  # 1400
    assert data["skus_at_risk"] == 1  # SKU-B: 20 < 30
    assert data["reorder_queue_count"] == 1


async def test_abc_matrix_empty():
    col = MagicMock()
    col.aggregate = MagicMock(return_value=_cursor([]))
    db = _multi_db(staging_sales=col)

    with patch("app.domains.inventory.abc_xyz_service.get_mongo_db", return_value=db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/inventory/abc")

    assert r.status_code == 200
    data = r.json()
    assert data["total_revenue"] == 0.0
    assert data["segments"]["A"] == []


async def test_abc_matrix_with_data():
    """ABC segments are computed from sales revenue."""
    col = _seq_col([
        {"_id": "SKU-A", "revenue": 800.0},
        {"_id": "SKU-B", "revenue": 100.0},
        {"_id": "SKU-C", "revenue": 60.0},
        {"_id": "SKU-D", "revenue": 40.0},
    ])
    db = _multi_db(staging_sales=col)

    with patch("app.domains.inventory.abc_xyz_service.get_mongo_db", return_value=db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/inventory/abc")

    assert r.status_code == 200
    data = r.json()
    assert "SKU-A" in data["segments"]["A"]
    assert "SKU-B" in data["segments"]["B"]
    assert data["sku_counts"]["A"] == 1
    assert data["sku_counts"]["C"] == 2


async def test_xyz_matrix_with_data():
    """XYZ segments returned with correct structure."""
    col = _seq_col([
        {"_id": {"sku": "SKU-X", "week": "2024-W01"}, "qty": 100.0},
        {"_id": {"sku": "SKU-X", "week": "2024-W02"}, "qty": 100.0},
        {"_id": {"sku": "SKU-Z", "week": "2024-W01"}, "qty": 500.0},
        {"_id": {"sku": "SKU-Z", "week": "2024-W08"}, "qty": 0.1},
    ])
    db = _multi_db(staging_sales=col)

    with patch("app.domains.inventory.abc_xyz_service.get_mongo_db", return_value=db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/inventory/xyz")

    assert r.status_code == 200
    data = r.json()
    assert "X" in data["segments"]
    assert "SKU-X" in data["segments"]["X"]


async def test_aging_empty():
    col = MagicMock()
    col.aggregate = MagicMock(return_value=_cursor([]))
    db = _multi_db(staging_operations=col)

    with patch("app.domains.inventory.aging_service.get_mongo_db", return_value=db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/inventory/aging")

    assert r.status_code == 200
    data = r.json()
    assert data["total_skus"] == 0
    assert data["buckets"] == []


async def test_aging_with_data():
    """Aging buckets are classified from DOH values."""
    ops_col = _seq_col(
        [{"_id": None, "max_date": "2024-01-31"}],
        [{"_id": "SKU-A", "total_stock": 100.0}],
    )
    sales_col = _seq_col([{"_id": "SKU-A", "total_qty": 280.0}])
    proc_col = _seq_col([{"_id": "SKU-A", "avg_cost": 10.0}])
    db = _multi_db(
        staging_operations=ops_col,
        staging_sales=sales_col,
        staging_procurement=proc_col,
    )

    with patch("app.domains.inventory.aging_service.get_mongo_db", return_value=db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/inventory/aging")

    assert r.status_code == 200
    data = r.json()
    # DOH = 100 / (280/28) = 10 days → "<30d"
    buckets = {b["bucket"]: b for b in data["buckets"]}
    assert "<30d" in buckets
    assert "SKU-A" in buckets["<30d"]["skus"]


async def test_valuation_with_data():
    ops_col = _seq_col(
        [{"_id": None, "max_date": "2024-01-31"}],
        [{"_id": "SKU-A", "total_stock": 100.0}],
    )
    proc_col = _seq_col([{"_id": "SKU-A", "avg_cost": 15.0, "supplier_id": "S01"}])
    sales_col = _seq_col([{"_id": "SKU-A", "total_revenue": 2000.0, "total_qty": 100.0}])
    db = _multi_db(
        staging_operations=ops_col,
        staging_procurement=proc_col,
        staging_sales=sales_col,
    )

    with patch("app.domains.inventory.valuation_service.get_mongo_db", return_value=db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/inventory/valuation")

    assert r.status_code == 200
    data = r.json()
    assert data["total_cost_value"] == pytest.approx(100.0 * 15.0)  # 1500
    assert data["total_retail_value"] == pytest.approx(100.0 * 20.0)  # 2000 (2000/100=20 per unit)
    assert len(data["by_category"]) >= 1


async def test_velocity_with_data():
    ops_col = _seq_col(
        [{"_id": None, "max_date": "2024-01-31"}],
        [{"_id": "SKU-A", "total_stock": 50.0}],
    )
    sales_col = _seq_col([{"_id": "SKU-A", "units_sold": 150.0, "revenue": 3000.0}])
    proc_col = _seq_col([{"_id": "SKU-A", "avg_cost": 10.0}])
    db = _multi_db(
        staging_operations=ops_col,
        staging_sales=sales_col,
        staging_procurement=proc_col,
    )

    with patch("app.domains.inventory.velocity_service.get_mongo_db", return_value=db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/inventory/velocity")

    assert r.status_code == 200
    data = r.json()
    # sell_through = 150 / (150 + 50) = 0.75
    assert data["avg_sell_through"] == pytest.approx(0.75, abs=0.01)
    assert data["total_skus_analyzed"] == 1
    assert len(data["fast_movers"]) >= 1


async def test_sku_list_with_data():
    ops_col = _seq_col(
        [{"_id": None, "max_date": "2024-01-31"}],
        [{"_id": "SKU-A", "total_stock": 100.0, "reorder_point": 50.0},
         {"_id": "SKU-B", "total_stock": 200.0, "reorder_point": 80.0}],
    )
    sales_col = _seq_col(
        [{"_id": "SKU-A", "total_qty": 140.0}, {"_id": "SKU-B", "total_qty": 280.0}],
        # ABC call
        [{"_id": "SKU-A", "revenue": 1000.0}, {"_id": "SKU-B", "revenue": 500.0}],
        # XYZ call
        [],
    )
    proc_col = _seq_col(
        [{"_id": "SKU-A", "avg_cost": 10.0}, {"_id": "SKU-B", "avg_cost": 20.0}],
    )
    db = _multi_db(
        staging_operations=ops_col,
        staging_sales=sales_col,
        staging_procurement=proc_col,
    )

    with (
        patch("app.domains.inventory.service.get_mongo_db", return_value=db),
        patch("app.domains.inventory.abc_xyz_service.get_mongo_db", return_value=db),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/inventory/skus?page=1&page_size=10")

    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert data["page"] == 1
    assert len(data["items"]) >= 1


async def test_inventory_auth_required():
    """Endpoint returns 403 when no auth token."""
    from app.domains.auth.dependencies import get_current_user
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/inventory/overview")

    app.dependency_overrides.clear()
    assert r.status_code == 403
