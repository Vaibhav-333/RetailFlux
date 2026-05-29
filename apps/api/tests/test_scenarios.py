"""Scenario Planner tests: engine regression tests + endpoint tests."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.domains.scenarios.engine import run_simulation, _validate_assumptions
from app.main import app
from app.models.user import User, UserRole

FAKE_UID = uuid.uuid4()
FAKE_CID = uuid.uuid4()
FAKE_SC_ID = uuid.uuid4()


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


# ── Engine unit tests ──────────────────────────────────────────────────────────

class TestValidateAssumptions:
    def test_defaults_applied_for_missing_keys(self):
        result = _validate_assumptions({})
        assert result["demand_shock_pct"] == 0.0
        assert result["price_change_pct"] == 0.0
        assert result["horizon_days"] == 90

    def test_values_clamped_to_bounds(self):
        result = _validate_assumptions({"demand_shock_pct": 99.0, "price_change_pct": -99.0})
        assert result["demand_shock_pct"] == 2.0   # upper bound
        assert result["price_change_pct"] == -0.5   # lower bound

    def test_horizon_clamped(self):
        result = _validate_assumptions({"horizon_days": 1000})
        assert result["horizon_days"] == 365

    def test_partial_assumptions_merged_with_defaults(self):
        result = _validate_assumptions({"demand_shock_pct": -0.10})
        assert result["demand_shock_pct"] == -0.10
        assert result["cogs_change_pct"] == 0.0  # default preserved


class TestSimulationEngine:
    BASELINE = {
        "daily_revenue": 10_000.0,
        "daily_cogs": 6_000.0,
        "daily_units": 200.0,
        "avg_price": 50.0,
        "avg_unit_cost": 30.0,
        "inventory_value": 500_000.0,
    }

    def test_no_change_scenario_has_zero_deltas(self):
        result = run_simulation(self.BASELINE, {})
        # With no changes, scenario == baseline (allowing float rounding)
        assert abs(result["deltas"]["revenue_pct"]) < 0.01
        assert abs(result["deltas"]["gross_profit_pct"]) < 0.01

    def test_demand_shock_reduces_revenue(self):
        result = run_simulation(self.BASELINE, {"demand_shock_pct": -0.20})
        assert result["deltas"]["revenue_pct"] < -10.0  # should be roughly -20% (plus price elasticity)
        assert result["scenario_totals"]["revenue"] < result["baseline_totals"]["revenue"]

    def test_price_increase_with_elasticity_effect(self):
        """10% price increase with ε=-1.2 means demand drops ~12% → net revenue should change."""
        result = run_simulation(self.BASELINE, {"price_change_pct": 0.10})
        # Price increases but demand falls; net revenue direction depends on elasticity
        # |ε| > 1 means elastic: revenue drops; |ε| < 1 means inelastic: revenue rises
        # Our default ε = -1.2 (elastic), so revenue should drop slightly
        assert "revenue_pct" in result["deltas"]
        assert result["scenario_totals"]["gross_margin_pct"] != result["baseline_totals"]["gross_margin_pct"]

    def test_cogs_reduction_improves_gp(self):
        result = run_simulation(self.BASELINE, {"cogs_change_pct": -0.10})
        assert result["scenario_totals"]["gross_profit"] > result["baseline_totals"]["gross_profit"]
        assert result["scenario_totals"]["gross_margin_pct"] > result["baseline_totals"]["gross_margin_pct"]

    def test_marketing_spend_increase_lifts_demand(self):
        result = run_simulation(self.BASELINE, {"marketing_spend_change_pct": 0.50})
        # +50% marketing × 0.25 elasticity = +12.5% demand lift
        assert result["deltas"]["units_sold_pct"] > 5.0

    def test_daily_series_length_matches_horizon(self):
        for horizon in [7, 30, 90]:
            result = run_simulation(self.BASELINE, {"horizon_days": horizon})
            assert len(result["daily_series"]) == horizon

    def test_daily_series_has_required_fields(self):
        result = run_simulation(self.BASELINE, {"horizon_days": 7})
        for day in result["daily_series"]:
            assert "date" in day
            assert "baseline_revenue" in day
            assert "scenario_revenue" in day
            assert "baseline_gp" in day
            assert "scenario_gp" in day

    def test_scenario_gp_ge_zero_for_valid_inputs(self):
        """Scenario gross profit should not go negative for normal assumptions."""
        result = run_simulation(self.BASELINE, {"demand_shock_pct": -0.30})
        assert result["scenario_totals"]["gross_profit"] > 0

    def test_result_has_all_required_top_level_keys(self):
        result = run_simulation(self.BASELINE, {})
        for key in ["assumptions", "baseline_totals", "scenario_totals", "deltas",
                    "daily_series", "key_drivers", "inventory_roll_forward"]:
            assert key in result

    def test_key_drivers_sorted_by_magnitude(self):
        result = run_simulation(
            self.BASELINE,
            {"demand_shock_pct": -0.20, "price_change_pct": 0.05}
        )
        drivers = result["key_drivers"]
        assert len(drivers) >= 2
        # Sorted descending by abs(impact)
        impacts = [abs(d["impact"]) for d in drivers]
        assert impacts == sorted(impacts, reverse=True)

    def test_empty_baseline_uses_defaults(self):
        """Engine must not raise on empty baseline dict."""
        result = run_simulation({}, {"demand_shock_pct": -0.10})
        assert result["baseline_totals"]["revenue"] > 0

    def test_inventory_roll_forward_present(self):
        result = run_simulation(self.BASELINE, {})
        rf = result["inventory_roll_forward"]
        assert "baseline_end_value" in rf
        assert "scenario_end_value" in rf
        assert rf["scenario_end_value"] >= 0.0

    def test_combined_assumptions_work(self):
        """Multiple assumptions applied together should not raise."""
        result = run_simulation(
            self.BASELINE,
            {
                "demand_shock_pct": 0.10,
                "price_change_pct": -0.05,
                "cogs_change_pct": 0.03,
                "marketing_spend_change_pct": 0.20,
                "horizon_days": 60,
            }
        )
        assert len(result["daily_series"]) == 60
        assert result["scenario_totals"]["revenue"] > 0


# ── Auth guard tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_scenarios_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/v1/scenarios")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_scenario_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/scenarios", json={"name": "Test"})
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_simulate_endpoint_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/scenarios/simulate", json={"assumptions": {}})
    assert r.status_code in (401, 403)


# ── Quick simulate endpoint ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_quick_simulate_returns_results():
    """POST /scenarios/simulate with authenticated user returns simulation results."""
    from app.domains.auth.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: _fake_user()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(
                "/api/v1/scenarios/simulate",
                headers={"Authorization": "Bearer test-token"},
                json={
                    "baseline": {
                        "daily_revenue": 10000.0,
                        "daily_cogs": 6000.0,
                        "daily_units": 200.0,
                    },
                    "assumptions": {
                        "demand_shock_pct": -0.15,
                        "horizon_days": 30,
                    },
                },
            )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    body = r.json()
    assert "baseline_totals" in body
    assert "scenario_totals" in body
    assert "deltas" in body
    assert "daily_series" in body
    assert len(body["daily_series"]) == 30


# ── CRUD endpoint tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_scenarios_returns_paginated_structure():
    """List endpoint returns items, total, page, page_size."""
    from app.domains.auth.dependencies import get_current_user
    from app.models.scenario import Scenario

    mock_sc = MagicMock(spec=Scenario)
    mock_sc.id = FAKE_SC_ID
    mock_sc.company_id = FAKE_CID
    mock_sc.name = "Test Scenario"
    mock_sc.description = None
    mock_sc.created_by = FAKE_UID
    mock_sc.assumptions = {}
    mock_sc.baseline_snapshot = None
    mock_sc.is_shared = False
    mock_sc.share_token = None
    mock_sc.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    mock_sc.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

    app.dependency_overrides[get_current_user] = lambda: _fake_user()
    try:
        with patch(
            "app.domains.scenarios.service.list_scenarios",
            new_callable=AsyncMock,
            return_value={"items": [mock_sc], "total": 1, "page": 1, "page_size": 20},
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.get(
                    "/api/v1/scenarios",
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
    assert body["total"] == 1


@pytest.mark.asyncio
async def test_create_scenario_returns_created_scenario():
    """POST /scenarios creates and returns scenario dict."""
    from app.domains.auth.dependencies import get_current_user
    from app.models.scenario import Scenario

    mock_sc = MagicMock(spec=Scenario)
    mock_sc.id = FAKE_SC_ID
    mock_sc.company_id = FAKE_CID
    mock_sc.name = "Q3 Downturn"
    mock_sc.description = "What if Q3 sees a demand drop?"
    mock_sc.created_by = FAKE_UID
    mock_sc.assumptions = {"demand_shock_pct": -0.20}
    mock_sc.baseline_snapshot = None
    mock_sc.is_shared = False
    mock_sc.share_token = None
    mock_sc.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    mock_sc.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

    app.dependency_overrides[get_current_user] = lambda: _fake_user()
    try:
        with patch(
            "app.domains.scenarios.service.create_scenario",
            new_callable=AsyncMock,
            return_value=mock_sc,
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.post(
                    "/api/v1/scenarios",
                    headers={"Authorization": "Bearer test-token"},
                    json={
                        "name": "Q3 Downturn",
                        "description": "What if Q3 sees a demand drop?",
                        "assumptions": {"demand_shock_pct": -0.20},
                    },
                )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Q3 Downturn"
    assert "assumptions" in body


@pytest.mark.asyncio
async def test_get_scenario_not_found_returns_404():
    from app.domains.auth.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: _fake_user()
    try:
        with patch(
            "app.domains.scenarios.service.get_scenario",
            new_callable=AsyncMock,
            side_effect=ValueError("Scenario not found"),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.get(
                    f"/api/v1/scenarios/{FAKE_SC_ID}",
                    headers={"Authorization": "Bearer test-token"},
                )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_run_scenario_returns_run_dict():
    """POST /scenarios/{id}/run returns a ScenarioRun dict with results."""
    from app.domains.auth.dependencies import get_current_user
    from app.models.scenario import Scenario, ScenarioRun

    mock_sc = MagicMock(spec=Scenario)
    mock_sc.id = FAKE_SC_ID
    mock_sc.assumptions = {"demand_shock_pct": -0.10, "horizon_days": 30}
    mock_sc.baseline_snapshot = {}
    mock_sc.runs = []

    mock_run = MagicMock(spec=ScenarioRun)
    mock_run.id = uuid.uuid4()
    mock_run.scenario_id = FAKE_SC_ID
    mock_run.run_by = FAKE_UID
    mock_run.assumptions_snapshot = {"demand_shock_pct": -0.10, "horizon_days": 30}
    mock_run.results = {"baseline_totals": {}, "scenario_totals": {}, "deltas": {}}
    mock_run.run_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

    app.dependency_overrides[get_current_user] = lambda: _fake_user()
    try:
        with (
            patch(
                "app.domains.scenarios.service.get_scenario",
                new_callable=AsyncMock,
                return_value=mock_sc,
            ),
            patch(
                "app.domains.scenarios.service.save_run",
                new_callable=AsyncMock,
                return_value=mock_run,
            ),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.post(
                    f"/api/v1/scenarios/{FAKE_SC_ID}/run",
                    headers={"Authorization": "Bearer test-token"},
                    json={},
                )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    body = r.json()
    assert "results" in body
    assert "assumptions_snapshot" in body
