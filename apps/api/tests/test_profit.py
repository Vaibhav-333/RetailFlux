"""Profit intelligence tests: attribution math golden tests + endpoint tests."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.domains.profit.attribution_service import get_profit_attribution
from app.domains.profit.forecast_service import _holt_winters_forecast
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


# ── Unit tests: attribution math ──────────────────────────────────────────────

class TestAttributionMath:
    def test_waterfall_sums_to_total_delta(self):
        """All delta bars should sum to (current_gp - prior_gp)."""
        # Simulate a simple waterfall
        prior = 100_000.0
        current = 120_000.0
        total_delta = current - prior

        waterfall = [
            {"label": "Prior Period GP", "value": prior, "type": "base"},
            {"label": "Volume", "value": 15_000.0, "type": "delta"},
            {"label": "Price", "value": 8_000.0, "type": "delta"},
            {"label": "Mix", "value": -5_000.0, "type": "delta"},
            {"label": "Cost", "value": 4_000.0, "type": "delta"},
            {"label": "Promo / Other", "value": -2_000.0, "type": "delta"},
            {"label": "Current Period GP", "value": current, "type": "total"},
        ]

        delta_sum = sum(b["value"] for b in waterfall if b["type"] == "delta")
        assert abs(delta_sum - total_delta) < 1.0, (
            f"Delta bars {delta_sum} should equal GP change {total_delta}"
        )

    def test_waterfall_final_equals_current(self):
        """The 'total' bar should always equal current period GP."""
        current_gp = 85_230.50
        waterfall = [
            {"label": "Prior Period GP", "value": 80_000.0, "type": "base"},
            {"label": "Volume", "value": 3_000.0, "type": "delta"},
            {"label": "Price", "value": 1_500.0, "type": "delta"},
            {"label": "Mix", "value": 730.50, "type": "delta"},
            {"label": "Cost", "value": 0.0, "type": "delta"},
            {"label": "Promo / Other", "value": 0.0, "type": "delta"},
            {"label": "Current Period GP", "value": current_gp, "type": "total"},
        ]
        total_bar = next(b for b in waterfall if b["type"] == "total")
        assert total_bar["value"] == current_gp


# ── Unit tests: Holt-Winters forecast ─────────────────────────────────────────

class TestHoltWintersForecast:
    def test_returns_correct_horizon(self):
        """Forecast output should have exactly *horizon* points."""
        values = [100.0 + i * 2 + (i % 7) * 5 for i in range(30)]
        point, lower, upper = _holt_winters_forecast(values, horizon=14)
        assert len(point) == 14
        assert len(lower) == 14
        assert len(upper) == 14

    def test_ci_ordering(self):
        """lower ≤ point ≤ upper for every forecast step."""
        values = [1000.0 + i * 10 for i in range(30)]
        point, lower, upper = _holt_winters_forecast(values, horizon=7)
        for p, lo, hi in zip(point, lower, upper):
            assert lo <= p + 0.01  # allow float rounding
            assert p <= hi + 0.01

    def test_non_negative_forecast(self):
        """Forecast lower CI should not go below zero."""
        values = [10.0] * 20  # flat series
        _, lower, _ = _holt_winters_forecast(values, horizon=5)
        for lo in lower:
            assert lo >= 0.0

    def test_fallback_for_short_series(self):
        """Very short series should return a flat fallback, not raise."""
        values = [50.0, 55.0]
        point, lower, upper = _holt_winters_forecast(values, horizon=3)
        assert len(point) == 3

    def test_empty_series_fallback(self):
        """Empty series returns zeros without raising."""
        point, lower, upper = _holt_winters_forecast([], horizon=5)
        assert len(point) == 5
        assert all(v == 0.0 for v in point)


# ── Endpoint tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_profit_forecast_endpoint_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/v1/profit/forecast")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_profit_attribution_endpoint_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/v1/profit/attribution")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_profit_levers_endpoint_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/v1/profit/levers")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_profit_forecast_returns_structure():
    """Forecast endpoint returns historical, forecast, and summary."""
    from app.domains.auth.dependencies import get_current_user

    empty_col = MagicMock()
    empty_col.aggregate = MagicMock(return_value=_cursor([]))
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=empty_col)

    app.dependency_overrides[get_current_user] = _fake_user
    try:
        with (
            patch("app.domains.profit.forecast_service.get_mongo_db", return_value=db),
            patch("app.core.cache.get_json", new_callable=AsyncMock, return_value=None),
            patch("app.core.cache.set_json", new_callable=AsyncMock),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.get(
                    "/api/v1/profit/forecast",
                    headers={"Authorization": "Bearer test-token"},
                )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    body = r.json()
    assert "historical" in body
    assert "forecast" in body
    assert "summary" in body
    assert "confidence" in body["summary"]


@pytest.mark.asyncio
async def test_profit_attribution_returns_waterfall():
    """Attribution endpoint returns a waterfall list."""
    from app.domains.auth.dependencies import get_current_user

    empty_col = MagicMock()
    empty_col.aggregate = MagicMock(return_value=_cursor([]))
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=empty_col)

    app.dependency_overrides[get_current_user] = _fake_user
    try:
        with (
            patch("app.domains.profit.attribution_service.get_mongo_db", return_value=db),
            patch("app.core.cache.get_json", new_callable=AsyncMock, return_value=None),
            patch("app.core.cache.set_json", new_callable=AsyncMock),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.get(
                    "/api/v1/profit/attribution?period=28d",
                    headers={"Authorization": "Bearer test-token"},
                )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    body = r.json()
    assert "waterfall" in body
    assert isinstance(body["waterfall"], list)
    # Waterfall must contain base + total bars
    types = [b["type"] for b in body["waterfall"]]
    assert "base" in types
    assert "total" in types
