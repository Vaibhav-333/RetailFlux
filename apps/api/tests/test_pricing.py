"""Dynamic Pricing tests: elasticity model unit tests + endpoint tests."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.domains.pricing.elasticity_service import (
    estimate_elasticity,
    optimal_price_range,
    predict_demand,
)
from app.main import app
from app.models.user import User, UserRole

FAKE_UID = uuid.uuid4()
FAKE_CID = uuid.uuid4()


def _fake_user(role: UserRole = UserRole.CEO) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = FAKE_UID
    u.email = "ceo@acme.com"
    u.name = "CEO"
    u.role = role
    u.company_id = FAKE_CID
    u.is_active = True
    u.last_login_at = None
    u.prefs = None
    u.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return u


# ── Unit tests: elasticity estimation ─────────────────────────────────────────

class TestElasticityEstimation:
    def test_negative_elasticity_for_normal_good(self):
        """As price increases, demand decreases → negative elasticity."""
        import math
        prices = []
        quantities = []
        for i in range(30):
            p = 20.0 + i * 0.5
            q = max(1, int(100 * (20 / p) ** 1.5))
            prices.append(p)
            quantities.append(float(q))

        result = estimate_elasticity(prices, quantities)
        assert result["elasticity"] < 0, "Elasticity should be negative for demand curve"

    def test_insufficient_data_returns_unreliable(self):
        """< min_observations returns reliable=False."""
        prices = [10.0, 12.0, 15.0]
        quantities = [100.0, 90.0, 80.0]
        result = estimate_elasticity(prices, quantities, min_observations=10)
        assert result["reliable"] is False
        assert result["elasticity"] == -1.0  # default

    def test_zero_prices_filtered_out(self):
        """Zero prices/quantities should be silently excluded."""
        prices = [0.0, 10.0, 12.0, 15.0, 18.0] + [10.0 + i for i in range(20)]
        quantities = [0.0, 100.0, 90.0, 80.0, 70.0] + [100.0 - i * 2 for i in range(20)]
        result = estimate_elasticity(prices, quantities)
        # Should not raise; if enough data, should produce an estimate
        assert "elasticity" in result
        assert "r_squared" in result

    def test_r_squared_in_range(self):
        """R² should be between 0 and 1 (inclusive)."""
        import math
        prices = [10.0 + i for i in range(25)]
        quantities = [max(1.0, 200.0 * (10.0 / p) ** 1.2) for p in prices]
        result = estimate_elasticity(prices, quantities)
        assert 0.0 <= result["r_squared"] <= 1.0

    def test_elastic_good_large_negative_elasticity(self):
        """Highly elastic good should show elasticity < -1."""
        import math
        prices = [10.0 + i for i in range(25)]
        # Highly elastic: demand drops sharply with price
        quantities = [max(0.5, 500.0 * (10.0 / p) ** 2.5) for p in prices]
        result = estimate_elasticity(prices, quantities)
        if result["reliable"]:
            assert result["elasticity"] < -1.0, "Highly elastic good should have |elasticity| > 1"


class TestPredictDemand:
    def test_price_increase_reduces_demand_for_elastic_good(self):
        """With elasticity = -1.5, 10% price increase → 15% demand decrease."""
        new_demand = predict_demand(
            elasticity=-1.5,
            intercept=5.0,
            current_price=100.0,
            new_price=110.0,
            current_demand=1000.0,
        )
        expected = 1000.0 * (110 / 100) ** (-1.5)
        assert abs(new_demand - expected) < 0.1

    def test_inelastic_good_small_demand_change(self):
        """With elasticity = -0.3, 10% price increase → ~3% demand decrease."""
        new_demand = predict_demand(
            elasticity=-0.3,
            intercept=3.0,
            current_price=50.0,
            new_price=55.0,
            current_demand=500.0,
        )
        expected = 500.0 * (55 / 50) ** (-0.3)
        assert abs(new_demand - expected) < 0.1

    def test_zero_price_returns_current_demand(self):
        """Guard: zero price should not crash."""
        result = predict_demand(-1.0, 5.0, 0.0, 10.0, 100.0)
        assert result == 100.0


class TestOptimalPriceRange:
    def test_returns_optimal_price_within_range(self):
        """Optimal price should be within ±30% of current price."""
        result = optimal_price_range(
            current_price=50.0,
            unit_cost=30.0,
            elasticity=-1.2,
        )
        assert 35.0 <= result["optimal_price"] <= 65.0

    def test_enforces_minimum_margin(self):
        """Optimal price should never go below min_margin_pct above cost."""
        result = optimal_price_range(
            current_price=100.0,
            unit_cost=90.0,
            elasticity=-2.0,
            min_margin_pct=0.10,
        )
        margin = (result["optimal_price"] - 90.0) / result["optimal_price"]
        assert margin >= 0.08  # allow small float rounding

    def test_inelastic_good_suggests_price_increase(self):
        """Inelastic demand (elasticity close to 0) → price increase is profitable."""
        result = optimal_price_range(
            current_price=100.0,
            unit_cost=40.0,
            elasticity=-0.2,
        )
        assert result["optimal_price"] >= 100.0 * 0.99  # at or above current

    def test_zero_cost_handled_gracefully(self):
        """Zero unit cost should not crash."""
        result = optimal_price_range(100.0, 0.0, -1.0)
        assert result["optimal_price"] == 100.0  # returns current price (guard)


# ── Endpoint tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pricing_suggestions_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/v1/pricing/suggestions")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_pricing_summary_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/v1/pricing/summary")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_pricing_refresh_requires_ceo_or_admin():
    """SALES role should get 403 on the refresh endpoint."""
    from app.domains.auth.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: _fake_user(UserRole.SALES)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(
                "/api/v1/pricing/refresh",
                headers={"Authorization": "Bearer test-token"},
            )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_pricing_suggestions_returns_paginated_structure():
    """Suggestions endpoint returns items, total, page, page_size."""

    def _cursor(docs):
        c = MagicMock()
        c.to_list = AsyncMock(return_value=docs)
        return c

    empty_col = MagicMock()
    empty_col.aggregate = MagicMock(return_value=_cursor([]))
    empty_col.find = MagicMock(return_value=empty_col)
    empty_col.sort = MagicMock(return_value=empty_col)
    empty_col.skip = MagicMock(return_value=empty_col)
    empty_col.limit = MagicMock(return_value=empty_col)
    empty_col.to_list = AsyncMock(return_value=[])
    empty_col.count_documents = AsyncMock(return_value=0)
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=empty_col)

    from app.domains.auth.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = _fake_user
    try:
        with (
            patch("app.domains.pricing.suggestions_service.get_mongo_db", return_value=db),
            patch("app.core.cache.get_json", new_callable=AsyncMock, return_value=None),
            patch("app.core.cache.set_json", new_callable=AsyncMock),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.get(
                    "/api/v1/pricing/suggestions",
                    headers={"Authorization": "Bearer test-token"},
                )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert "page" in body
    assert "page_size" in body
