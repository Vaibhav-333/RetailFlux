"""Extended tool registry for the AI Copilot (~30 tools across all domains).

All tool functions in the registry accept a single `company_id: str` parameter.
Functions that need additional parameters (db session, UUIDs) are wrapped here
so the tool-calling code stays uniform.

Role-based access control is enforced via ROLE_TOOL_ACCESS.
"""
from __future__ import annotations

import uuid as _uuid

from app.domains.analytics.sales_service import get_sales_kpis
from app.domains.analytics.marketing_service import get_marketing_kpis
from app.domains.analytics.operations_service import get_operations_kpis
from app.domains.analytics.finance_service import get_finance_kpis
from app.domains.analytics.procurement_service import get_procurement_kpis
from app.domains.analytics.summary_service import get_dashboard_summary
from app.domains.insights.anomaly_service import get_revenue_anomalies
from app.domains.forecasting.top_skus_forecast import get_top_skus_forecast

# Inventory tools (all accept company_id: str only)
from app.domains.inventory.service import get_inventory_overview
from app.domains.inventory.abc_xyz_service import get_abc_xyz_matrix
from app.domains.inventory.aging_service import get_aging_buckets
from app.domains.inventory.reorder_service import get_reorder_queue
from app.domains.inventory.valuation_service import get_valuation
from app.domains.inventory.velocity_service import get_velocity
from app.domains.inventory.scoring_service import get_health_scores
from app.domains.inventory.anomaly_service import get_inventory_anomalies


# ── Task tool wrappers ────────────────────────────────────────────────────────
# Task analytics functions need a db session; wrap them to open their own.

async def _get_department_productivity(company_id: str) -> list:
    from app.core.database import AsyncSessionLocal  # noqa: PLC0415
    from app.domains.tasks.analytics_service import get_department_productivity  # noqa: PLC0415

    async with AsyncSessionLocal() as db:
        return await get_department_productivity(db, _uuid.UUID(company_id))


async def _get_workload(company_id: str) -> list:
    from app.core.database import AsyncSessionLocal  # noqa: PLC0415
    from app.domains.tasks.analytics_service import get_workload  # noqa: PLC0415

    async with AsyncSessionLocal() as db:
        return await get_workload(db, _uuid.UUID(company_id))


async def _get_bottlenecks(company_id: str) -> list:
    from app.core.database import AsyncSessionLocal  # noqa: PLC0415
    from app.domains.tasks.analytics_service import get_bottlenecks  # noqa: PLC0415

    async with AsyncSessionLocal() as db:
        return await get_bottlenecks(db, _uuid.UUID(company_id))


async def _simulate_demand_shock(company_id: str) -> dict:
    """Simulate a -20% demand shock scenario to see revenue and margin impact."""
    from app.domains.scenarios.engine import run_simulation  # noqa: PLC0415
    from app.domains.analytics.finance_service import get_finance_kpis  # noqa: PLC0415

    try:
        finance = await get_finance_kpis(company_id)
        days = 90
        baseline = {
            "daily_revenue": finance.get("total_revenue", 0) / days,
            "daily_cogs": finance.get("total_cogs", 0) / days,
            "daily_units": 100.0,
            "avg_price": 50.0,
            "avg_unit_cost": 30.0,
            "inventory_value": 500_000.0,
        }
    except Exception:
        baseline = {}

    results = run_simulation(baseline, {"demand_shock_pct": -0.20, "horizon_days": 90})
    return {
        "scenario": "20% demand shock",
        "baseline_gp": results["baseline_totals"]["gross_profit"],
        "scenario_gp": results["scenario_totals"]["gross_profit"],
        "gp_delta_pct": results["deltas"]["gross_profit_pct"],
        "revenue_delta_pct": results["deltas"]["revenue_pct"],
        "key_drivers": results["key_drivers"],
    }


async def _simulate_price_increase(company_id: str) -> dict:
    """Simulate a +10% price increase scenario accounting for demand elasticity."""
    from app.domains.scenarios.engine import run_simulation  # noqa: PLC0415
    from app.domains.analytics.finance_service import get_finance_kpis  # noqa: PLC0415

    try:
        finance = await get_finance_kpis(company_id)
        days = 90
        baseline = {
            "daily_revenue": finance.get("total_revenue", 0) / days,
            "daily_cogs": finance.get("total_cogs", 0) / days,
            "daily_units": 100.0,
            "avg_price": 50.0,
            "avg_unit_cost": 30.0,
            "inventory_value": 500_000.0,
        }
    except Exception:
        baseline = {}

    results = run_simulation(baseline, {"price_change_pct": 0.10, "horizon_days": 90})
    return {
        "scenario": "10% price increase",
        "baseline_gp": results["baseline_totals"]["gross_profit"],
        "scenario_gp": results["scenario_totals"]["gross_profit"],
        "gp_delta_pct": results["deltas"]["gross_profit_pct"],
        "margin_pp_change": results["deltas"]["gross_margin_pp"],
        "units_sold_pct": results["deltas"]["units_sold_pct"],
        "key_drivers": results["key_drivers"],
    }


async def _get_task_summary(company_id: str) -> dict:
    """Simple open-task count summary per status for CEO-level overview."""
    from app.core.database import AsyncSessionLocal  # noqa: PLC0415
    from sqlalchemy import text  # noqa: PLC0415

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("""
                SELECT status, priority, COUNT(*) AS cnt
                FROM app.tasks
                WHERE company_id = :cid AND deleted_at IS NULL
                GROUP BY status, priority
                ORDER BY status, priority
            """),
            {"cid": company_id},
        )
        rows = result.fetchall()
    by_status: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    for status, priority, cnt in rows:
        by_status[status] = by_status.get(status, 0) + cnt
        by_priority[priority] = by_priority.get(priority, 0) + cnt
    return {"by_status": by_status, "by_priority": by_priority, "total": sum(by_status.values())}


# ── Registry ──────────────────────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, dict] = {
    # ── Analytics ──────────────────────────────────────────────────────────────
    "get_sales_kpis": {
        "fn": get_sales_kpis,
        "description": "Get sales KPIs: total revenue, order count, AOV, top SKUs, revenue by region, daily trend.",
        "dept": "sales",
    },
    "get_marketing_kpis": {
        "fn": get_marketing_kpis,
        "description": "Get marketing KPIs: ad spend, ROAS, CAC, CTR, top campaigns, daily spend trend.",
        "dept": "marketing",
    },
    "get_operations_kpis": {
        "fn": get_operations_kpis,
        "description": "Get operations KPIs: total SKUs, stock units, warehouses, SKUs below reorder.",
        "dept": "operations",
    },
    "get_finance_kpis": {
        "fn": get_finance_kpis,
        "description": "Get finance KPIs: revenue, COGS, gross profit, gross margin, monthly P&L.",
        "dept": "finance",
    },
    "get_procurement_kpis": {
        "fn": get_procurement_kpis,
        "description": "Get procurement KPIs: total spend, units ordered, unique suppliers, avg lead days.",
        "dept": "procurement",
    },
    "get_dashboard_summary": {
        "fn": get_dashboard_summary,
        "description": "Get CEO dashboard summary combining KPIs from all 5 departments plus revenue sparkline.",
        "dept": None,
    },
    # ── AI insights & forecasting ──────────────────────────────────────────────
    "get_revenue_anomalies": {
        "fn": get_revenue_anomalies,
        "description": "Detect revenue anomalies (spikes/drops) using z-score analysis on daily revenue.",
        "dept": None,
    },
    "get_top_skus_forecast": {
        "fn": get_top_skus_forecast,
        "description": "Get 30-day demand forecast for top-5 revenue SKUs using Holt-Winters time-series.",
        "dept": None,
    },
    # ── Inventory ─────────────────────────────────────────────────────────────
    "get_inventory_overview": {
        "fn": get_inventory_overview,
        "description": "Get inventory KPI strip: total value, health score, SKUs at risk, reorder queue count.",
        "dept": "operations",
    },
    "get_abc_xyz_matrix": {
        "fn": get_abc_xyz_matrix,
        "description": "Get ABC×XYZ inventory matrix showing SKU segments by revenue and demand variability.",
        "dept": "operations",
    },
    "get_aging_buckets": {
        "fn": get_aging_buckets,
        "description": "Get inventory aging by days-on-hand bucket (<30d, 30-60, 60-90, 90-180, 180+).",
        "dept": "operations",
    },
    "get_reorder_queue": {
        "fn": get_reorder_queue,
        "description": "Get ranked reorder recommendations with EOQ math, safety stock, and urgency scores.",
        "dept": "operations",
    },
    "get_inventory_valuation": {
        "fn": get_valuation,
        "description": "Get total inventory value at cost and retail by category.",
        "dept": "finance",
    },
    "get_velocity_report": {
        "fn": get_velocity,
        "description": "Get sell-through rate, turnover, and fast/slow mover classification per SKU.",
        "dept": "operations",
    },
    "get_health_score_distribution": {
        "fn": get_health_scores,
        "description": "Get distribution of inventory health scores (0-100) and top/bottom 20 SKUs by score.",
        "dept": "operations",
    },
    "get_inventory_anomalies": {
        "fn": get_inventory_anomalies,
        "description": "Detect inventory demand anomalies using IsolationForest on SKU demand and sell-through.",
        "dept": "operations",
    },
    # ── Scenario simulations ──────────────────────────────────────────────────
    "simulate_demand_shock": {
        "fn": _simulate_demand_shock,
        "description": "Simulate a -20% demand shock: shows revenue, GP, and margin impact over 90 days.",
        "dept": None,
    },
    "simulate_price_increase": {
        "fn": _simulate_price_increase,
        "description": "Simulate a +10% price increase: shows demand elasticity effect on revenue and GP.",
        "dept": None,
    },
    # ── Tasks ─────────────────────────────────────────────────────────────────
    "get_task_summary": {
        "fn": _get_task_summary,
        "description": "Get task summary: open, in-progress, blocked, done counts by status and priority.",
        "dept": None,
    },
    "get_department_productivity": {
        "fn": _get_department_productivity,
        "description": "Get department-level task productivity: completion rate by department.",
        "dept": None,
    },
    "get_workload_snapshot": {
        "fn": _get_workload,
        "description": "Get current open-task workload per user for capacity planning.",
        "dept": None,
    },
    "get_bottleneck_report": {
        "fn": _get_bottlenecks,
        "description": "Get AI-detected task bottlenecks: stuck tasks, stalled dependencies, SLA breaches.",
        "dept": None,
    },
}


# ── Role-based access ─────────────────────────────────────────────────────────

_DEPT_TOOLS: dict[str, set[str]] = {
    "sales": {
        "get_sales_kpis", "get_dashboard_summary",
        "get_revenue_anomalies", "get_top_skus_forecast", "get_task_summary",
    },
    "marketing": {"get_marketing_kpis", "get_dashboard_summary", "get_task_summary"},
    "operations": {
        "get_operations_kpis", "get_dashboard_summary",
        "get_inventory_overview", "get_abc_xyz_matrix", "get_aging_buckets",
        "get_reorder_queue", "get_velocity_report", "get_health_score_distribution",
        "get_inventory_anomalies", "get_task_summary", "get_workload_snapshot",
    },
    "finance": {
        "get_finance_kpis", "get_dashboard_summary",
        "get_inventory_valuation", "get_task_summary",
        "simulate_demand_shock", "simulate_price_increase",
    },
    "procurement": {
        "get_procurement_kpis", "get_dashboard_summary",
        "get_reorder_queue", "get_task_summary",
    },
}

ROLE_TOOL_ACCESS: dict[str, set[str] | None] = {
    "ceo": None,
    "admin": None,
    **{dept: tools for dept, tools in _DEPT_TOOLS.items()},
}


def get_tools_for_role(role: str) -> dict[str, dict]:
    allowed = ROLE_TOOL_ACCESS.get(role)
    if allowed is None:
        return TOOL_REGISTRY
    return {k: v for k, v in TOOL_REGISTRY.items() if k in allowed}


def build_tool_menu(tools: dict[str, dict]) -> str:
    return "\n".join(f'- "{name}": {info["description"]}' for name, info in tools.items())
