"""Predictive Profit Intelligence — 90-day gross-profit forecast with CI band.

Algorithm:
  1. Pull daily revenue + COGS from staging collections.
  2. Fit per-category Holt-Winters (additive trend + seasonal) via statsmodels.
  3. Aggregate category forecasts → company total.
  4. Persist in Mongo ``profit_forecasts`` (keyed by company_id + generated_at date).
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Optional

import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from app.core.cache import FORECAST_TTL, get_json, set_json
from app.core.mongodb import get_mongo_db

_CACHE_PREFIX = "rf:cache:profit:forecast"


def _cache_key(company_id: str) -> str:
    return f"{_CACHE_PREFIX}:{company_id}"


def _holt_winters_forecast(
    values: list[float],
    horizon: int = 90,
    seasonal_periods: int = 7,
) -> tuple[list[float], list[float], list[float]]:
    """Return (point_forecast, lower_ci, upper_ci) each of length *horizon*.

    Falls back to linear extrapolation if the series is too short for HW.
    """
    if len(values) < 2 * seasonal_periods + 2:
        # Linear fallback
        if len(values) < 2:
            flat = [float(values[-1]) if values else 0.0] * horizon
            return flat, flat, flat
        trend = np.polyfit(range(len(values)), values, 1)
        start = len(values)
        point = [max(0.0, float(np.polyval(trend, start + i))) for i in range(horizon)]
        std = float(np.std(values)) if len(values) > 1 else 0.0
        lower = [max(0.0, p - 1.65 * std) for p in point]
        upper = [p + 1.65 * std for p in point]
        return point, lower, upper

    try:
        model = ExponentialSmoothing(
            values,
            trend="add",
            seasonal="add",
            seasonal_periods=seasonal_periods,
            initialization_method="estimated",
        ).fit(optimized=True, use_brute=False)
        forecast = model.forecast(horizon)
        std_err = np.sqrt(model.sse / max(1, len(values) - 3))
        point = [max(0.0, float(v)) for v in forecast]
        lower = [max(0.0, p - 1.65 * std_err) for p in point]
        upper = [p + 1.65 * std_err for p in point]
        return point, lower, upper
    except Exception:
        flat = [float(np.mean(values))] * horizon
        std = float(np.std(values)) if len(values) > 1 else 0.0
        return flat, [max(0.0, f - 1.65 * std) for f in flat], [f + 1.65 * std for f in flat]


async def _fetch_daily_pnl(company_id: str, days: int = 180) -> dict[str, dict[str, float]]:
    """Return {date_str: {revenue, cogs, gross_profit}} for last *days* days."""
    db = get_mongo_db()
    col_sales = db["staging_sales"]
    col_proc = db["staging_procurement"]

    cutoff = (date.today() - timedelta(days=days)).isoformat()

    rev_docs, cogs_docs = await asyncio.gather(
        col_sales.aggregate([
            {"$match": {"_company_id": company_id, "date": {"$gte": cutoff}}},
            {"$group": {
                "_id": "$date",
                "revenue": {"$sum": "$revenue"},
            }},
            {"$sort": {"_id": 1}},
        ]).to_list(length=days + 10),
        col_proc.aggregate([
            {"$match": {"_company_id": company_id, "date": {"$gte": cutoff}}},
            {"$group": {
                "_id": "$date",
                "cogs": {"$sum": {"$multiply": ["$unit_cost", "$quantity"]}},
            }},
            {"$sort": {"_id": 1}},
        ]).to_list(length=days + 10),
    )

    rev_map = {d["_id"]: float(d.get("revenue", 0)) for d in rev_docs}
    cogs_map = {d["_id"]: float(d.get("cogs", 0)) for d in cogs_docs}

    all_dates = sorted(set(rev_map) | set(cogs_map))
    result: dict[str, dict[str, float]] = {}
    for dt in all_dates:
        rev = rev_map.get(dt, 0.0)
        cogs = cogs_map.get(dt, 0.0)
        result[dt] = {
            "revenue": rev,
            "cogs": cogs,
            "gross_profit": rev - cogs,
        }
    return result


async def get_profit_forecast(company_id: str) -> dict:
    """Build 90-day gross-profit forecast and return structured response."""
    cache_key = _cache_key(company_id)
    hit = await get_json(cache_key)
    if hit:
        return hit

    daily_pnl = await _fetch_daily_pnl(company_id, days=180)

    if not daily_pnl:
        result = {
            "generated_at": date.today().isoformat(),
            "historical": [],
            "forecast": [],
            "summary": {
                "forecast_90d_revenue": 0.0,
                "forecast_90d_cogs": 0.0,
                "forecast_90d_gross_profit": 0.0,
                "forecast_gross_margin_pct": 0.0,
                "confidence": "low",
            },
        }
        await set_json(cache_key, result, FORECAST_TTL)
        return result

    dates = sorted(daily_pnl.keys())
    rev_series = [daily_pnl[d]["revenue"] for d in dates]
    gp_series = [daily_pnl[d]["gross_profit"] for d in dates]
    cogs_series = [daily_pnl[d]["cogs"] for d in dates]

    horizon = 90
    gp_point, gp_lower, gp_upper = _holt_winters_forecast(gp_series, horizon=horizon)
    rev_point, _, _ = _holt_winters_forecast(rev_series, horizon=horizon)
    cogs_point, _, _ = _holt_winters_forecast(cogs_series, horizon=horizon)

    last_date = date.fromisoformat(dates[-1])
    forecast_dates = [
        (last_date + timedelta(days=i + 1)).isoformat() for i in range(horizon)
    ]

    # Compute avg gross margin % from last 28d as confidence proxy
    last_28 = gp_series[-28:] if len(gp_series) >= 28 else gp_series
    last_28_rev = rev_series[-28:] if len(rev_series) >= 28 else rev_series
    avg_margin = (
        float(np.mean(last_28)) / max(1.0, float(np.mean(last_28_rev))) * 100
        if last_28_rev else 0.0
    )
    ci_width_ratio = (
        float(np.mean([u - l for u, l in zip(gp_upper, gp_lower)]))
        / max(1.0, abs(float(np.mean(gp_point))))
    )
    confidence = "high" if ci_width_ratio < 0.2 else ("medium" if ci_width_ratio < 0.5 else "low")

    result = {
        "generated_at": date.today().isoformat(),
        "historical": [
            {
                "date": d,
                "revenue": round(daily_pnl[d]["revenue"], 2),
                "cogs": round(daily_pnl[d]["cogs"], 2),
                "gross_profit": round(daily_pnl[d]["gross_profit"], 2),
            }
            for d in dates[-90:]  # Return last 90 days of history
        ],
        "forecast": [
            {
                "date": forecast_dates[i],
                "revenue": round(max(0.0, rev_point[i]), 2),
                "cogs": round(max(0.0, cogs_point[i]), 2),
                "gross_profit": round(gp_point[i], 2),
                "gp_lower": round(gp_lower[i], 2),
                "gp_upper": round(gp_upper[i], 2),
            }
            for i in range(horizon)
        ],
        "summary": {
            "forecast_90d_revenue": round(sum(rev_point), 2),
            "forecast_90d_cogs": round(sum(cogs_point), 2),
            "forecast_90d_gross_profit": round(sum(gp_point), 2),
            "forecast_gross_margin_pct": round(avg_margin, 2),
            "confidence": confidence,
            "ci_width_pct": round(ci_width_ratio * 100, 1),
        },
    }

    await set_json(cache_key, result, FORECAST_TTL)
    return result
