"""Inventory seasonality: STL decomposition per SKU using statsmodels."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import pandas as pd

from app.core.cache import ANALYTICS_TTL, get_json, inventory_key, set_json
from app.core.mongodb import get_mongo_db
from app.schemas.inventory import SeasonalityOut, SeasonalityPoint


# Minimum days of data required for STL
_MIN_DAYS = 21  # 3 full weeks


def _stl_decompose(
    dates: list[str],
    values: list[float],
    period: int = 7,
) -> tuple[list[float], list[float], list[float]]:
    """Run statsmodels STL. Returns (trend, seasonal, residual) arrays.

    Falls back to pandas rolling mean if STL fails.
    """
    try:
        from statsmodels.tsa.seasonal import STL  # noqa: PLC0415

        series = pd.Series(values, dtype=float)
        stl = STL(series, period=period, robust=True)
        res = stl.fit()
        return (
            list(res.trend),
            list(res.seasonal),
            list(res.resid),
        )
    except Exception:
        pass

    # Fallback: rolling mean as "trend", residual as seasonal proxy
    s = pd.Series(values, dtype=float)
    trend = s.rolling(window=min(7, len(s)), center=True, min_periods=1).mean().tolist()
    seasonal = [v - t for v, t in zip(values, trend)]
    residual = [0.0] * len(values)
    return trend, seasonal, residual


async def get_seasonality(company_id: str, sku: str) -> SeasonalityOut:
    """Decompose a SKU's demand into trend + seasonal + residual components."""
    cache_key = inventory_key(f"seasonality:{sku}", company_id)
    hit = await get_json(cache_key)
    if hit:
        return SeasonalityOut(**hit)

    db = get_mongo_db()
    col_sales = db["staging_sales"]

    date_90d = (date.today() - timedelta(days=90)).isoformat()

    docs = await col_sales.aggregate([
        {"$match": {"_company_id": company_id, "sku": sku, "date": {"$gte": date_90d}}},
        {"$group": {"_id": "$date", "qty": {"$sum": "$quantity"}}},
        {"$sort": {"_id": 1}},
    ]).to_list(length=200)

    if len(docs) < _MIN_DAYS:
        return SeasonalityOut(
            sku=sku,
            trend=[],
            seasonal=[],
            residual=[],
            period_days=7,
            has_yearly_pattern=False,
        )

    dates = [d["_id"] for d in docs]
    values = [float(d.get("qty", 0)) for d in docs]

    # Fill gaps in date range with zeros
    if dates:
        start_dt = date.fromisoformat(dates[0])
        end_dt = date.fromisoformat(dates[-1])
        full_dates = [
            (start_dt + timedelta(days=i)).isoformat()
            for i in range((end_dt - start_dt).days + 1)
        ]
        date_value_map = dict(zip(dates, values))
        filled_values = [date_value_map.get(d, 0.0) for d in full_dates]
        dates = full_dates
        values = filled_values

    trend_arr, seasonal_arr, residual_arr = _stl_decompose(dates, values, period=7)

    trend = [SeasonalityPoint(date=d, value=round(v, 3)) for d, v in zip(dates, trend_arr)]
    seasonal = [SeasonalityPoint(date=d, value=round(v, 3)) for d, v in zip(dates, seasonal_arr)]
    residual = [SeasonalityPoint(date=d, value=round(v, 3)) for d, v in zip(dates, residual_arr)]

    # Has yearly pattern heuristic: if seasonal component amplitude > 20% of mean demand
    mean_demand = sum(values) / len(values) if values else 0
    seasonal_amplitude = (max(seasonal_arr) - min(seasonal_arr)) if seasonal_arr else 0
    has_yearly = len(dates) >= 28 and seasonal_amplitude > mean_demand * 0.2

    result = SeasonalityOut(
        sku=sku,
        trend=trend,
        seasonal=seasonal,
        residual=residual,
        period_days=7,
        has_yearly_pattern=has_yearly,
    )
    await set_json(cache_key, result.model_dump(), ANALYTICS_TTL * 12)  # Cache 1 hour
    return result
