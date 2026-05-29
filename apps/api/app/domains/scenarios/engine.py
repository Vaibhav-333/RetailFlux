"""Scenario simulation engine: numpy-based retail digital twin.

Assumptions schema
------------------
{
    "demand_shock_pct": 0.0,           # -0.99 to +2.0  overall demand multiplier
    "price_change_pct": 0.0,           # -0.5  to +1.0  selling price change
    "cogs_change_pct": 0.0,            # -0.5  to +1.0  unit cost change
    "marketing_spend_change_pct": 0.0, # -1.0  to +3.0  marketing budget change
    "lead_time_change_days": 0,        # integer days delta (affects inventory)
    "horizon_days": 90                 # 7–365 projection window
}

Marketing-demand elasticity: +10% marketing spend → +2.5% demand (ε = 0.25).
Price-demand elasticity: fashion retail default ε = -1.2 (moderate).
"""
from __future__ import annotations

from datetime import date, timedelta


MARKETING_ELASTICITY = 0.25  # fraction of marketing_spend_change → demand
PRICE_ELASTICITY = -1.2       # fashion retail default


def _validate_assumptions(raw: dict) -> dict:
    defaults: dict = {
        "demand_shock_pct": 0.0,
        "price_change_pct": 0.0,
        "cogs_change_pct": 0.0,
        "marketing_spend_change_pct": 0.0,
        "lead_time_change_days": 0,
        "horizon_days": 90,
    }
    merged = {**defaults, **raw}
    merged["demand_shock_pct"] = max(-0.99, min(2.0, float(merged["demand_shock_pct"])))
    merged["price_change_pct"] = max(-0.5, min(1.0, float(merged["price_change_pct"])))
    merged["cogs_change_pct"] = max(-0.5, min(1.0, float(merged["cogs_change_pct"])))
    merged["marketing_spend_change_pct"] = max(-1.0, min(3.0, float(merged["marketing_spend_change_pct"])))
    merged["lead_time_change_days"] = max(-30, min(60, int(merged["lead_time_change_days"])))
    merged["horizon_days"] = max(7, min(365, int(merged["horizon_days"])))
    return merged


def run_simulation(baseline: dict, assumptions: dict) -> dict:
    """Simulate scenario KPIs and daily time series.

    Parameters
    ----------
    baseline:
        Snapshot of current business metrics (all floats):
        ``daily_revenue``, ``daily_cogs``, ``daily_units``, ``avg_price``,
        ``avg_unit_cost``, ``marketing_spend_daily``, ``inventory_value``.
        Missing keys default to conservative retail-sized values.
    assumptions:
        Assumption-delta dict (see module docstring).

    Returns
    -------
    dict with keys:
        ``assumptions``, ``baseline_totals``, ``scenario_totals``,
        ``deltas``, ``daily_series``, ``key_drivers``,
        ``inventory_roll_forward``.
    """
    assumptions = _validate_assumptions(assumptions)
    h = assumptions["horizon_days"]

    # Baseline daily values (with sensible defaults)
    base_rev = float(baseline.get("daily_revenue") or 10_000.0)
    base_cogs = float(baseline.get("daily_cogs") or 6_000.0)
    base_units = float(baseline.get("daily_units") or 100.0)
    base_price = float(baseline.get("avg_price") or (base_rev / max(base_units, 1)))
    base_unit_cost = float(baseline.get("avg_unit_cost") or (base_cogs / max(base_units, 1)))
    inv_value = float(baseline.get("inventory_value") or 500_000.0)

    # Scenario multipliers
    marketing_lift = MARKETING_ELASTICITY * assumptions["marketing_spend_change_pct"]
    price_demand_effect = (
        (1.0 + assumptions["price_change_pct"]) ** PRICE_ELASTICITY
        if assumptions["price_change_pct"] != 0.0
        else 1.0
    )
    demand_mult = (
        (1.0 + assumptions["demand_shock_pct"])
        * (1.0 + marketing_lift)
        * price_demand_effect
    )
    price_mult = 1.0 + assumptions["price_change_pct"]
    cost_mult = 1.0 + assumptions["cogs_change_pct"]

    scen_units_daily = base_units * demand_mult
    scen_rev_daily = scen_units_daily * (base_price * price_mult)
    scen_cogs_daily = scen_units_daily * (base_unit_cost * cost_mult)

    # Day-of-week and slight linear growth coefficients
    _DOW_MULT = {0: 1.00, 1: 0.98, 2: 1.00, 3: 1.02, 4: 1.20, 5: 1.15, 6: 0.80}
    start = date.today()

    daily_series = []
    for i in range(h):
        d = start + timedelta(days=i)
        dow = d.weekday()
        dow_m = _DOW_MULT.get(dow, 1.0)
        trend_m = 1.0 + (i / h) * 0.05  # 5% secular growth across horizon

        b_rev = round(base_rev * dow_m * trend_m, 2)
        b_cogs_d = round(base_cogs * dow_m * trend_m, 2)
        s_rev = round(scen_rev_daily * dow_m * trend_m, 2)
        s_cogs_d = round(scen_cogs_daily * dow_m * trend_m, 2)

        daily_series.append({
            "date": d.isoformat(),
            "baseline_revenue": b_rev,
            "baseline_gp": round(b_rev - b_cogs_d, 2),
            "scenario_revenue": s_rev,
            "scenario_gp": round(s_rev - s_cogs_d, 2),
        })

    # Period totals (simplified, no DOW noise for comparability)
    base_rev_total = round(base_rev * h, 2)
    base_cogs_total = round(base_cogs * h, 2)
    base_gp_total = round(base_rev_total - base_cogs_total, 2)
    base_margin = base_gp_total / base_rev_total if base_rev_total else 0.0

    scen_rev_total = round(scen_rev_daily * h, 2)
    scen_cogs_total = round(scen_cogs_daily * h, 2)
    scen_gp_total = round(scen_rev_total - scen_cogs_total, 2)
    scen_margin = scen_gp_total / scen_rev_total if scen_rev_total else 0.0

    # Inventory roll-forward
    net_consumption = scen_cogs_daily * h
    inv_scenario = round(max(0.0, inv_value - net_consumption * 0.5), 2)

    # Key driver attribution
    demand_impact = round((demand_mult - 1.0) * base_rev_total, 2)
    price_impact = round(assumptions["price_change_pct"] * base_rev_total, 2)
    cost_savings = round(-(cost_mult - 1.0) * base_cogs_total, 2)
    marketing_impact = round(marketing_lift * base_rev_total, 2)

    key_drivers = sorted(
        [
            {"name": "Demand change", "impact": demand_impact,
             "impact_pct": round((demand_mult - 1.0) * 100, 2)},
            {"name": "Price change", "impact": price_impact,
             "impact_pct": round(assumptions["price_change_pct"] * 100, 2)},
            {"name": "COGS change", "impact": cost_savings,
             "impact_pct": round(-(cost_mult - 1.0) * 100, 2)},
            {"name": "Marketing lift", "impact": marketing_impact,
             "impact_pct": round(marketing_lift * 100, 2)},
        ],
        key=lambda x: abs(x["impact"]),
        reverse=True,
    )

    return {
        "assumptions": assumptions,
        "baseline_totals": {
            "revenue": base_rev_total,
            "cogs": base_cogs_total,
            "gross_profit": base_gp_total,
            "gross_margin_pct": round(base_margin * 100, 2),
            "units_sold": round(base_units * h, 0),
        },
        "scenario_totals": {
            "revenue": scen_rev_total,
            "cogs": scen_cogs_total,
            "gross_profit": scen_gp_total,
            "gross_margin_pct": round(scen_margin * 100, 2),
            "units_sold": round(scen_units_daily * h, 0),
        },
        "deltas": {
            "revenue_pct": round((scen_rev_total / base_rev_total - 1) * 100, 2)
            if base_rev_total else 0.0,
            "gross_profit_pct": round((scen_gp_total / base_gp_total - 1) * 100, 2)
            if base_gp_total else 0.0,
            "gross_margin_pp": round((scen_margin - base_margin) * 100, 2),
            "units_sold_pct": round((demand_mult - 1.0) * 100, 2),
        },
        "daily_series": daily_series,
        "key_drivers": key_drivers,
        "inventory_roll_forward": {
            "baseline_end_value": round(inv_value, 2),
            "scenario_end_value": inv_scenario,
        },
    }
