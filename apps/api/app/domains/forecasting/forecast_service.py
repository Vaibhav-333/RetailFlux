import asyncio
from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.core.mongodb import get_mongo_db
from app.schemas.forecast import ForecastPoint, SkuForecast


async def get_sku_forecast(
    company_id: str,
    sku: str,
    horizon_days: int = 30,
) -> SkuForecast:
    col = get_mongo_db()["staging_sales"]
    date_from = (date.today() - timedelta(days=90)).isoformat()
    date_to = date.today().isoformat()

    docs = await col.aggregate([
        {"$match": {
            "_company_id": company_id,
            "sku": sku,
            "date": {"$gte": date_from, "$lte": date_to},
        }},
        {"$group": {"_id": "$date", "revenue": {"$sum": "$revenue"}}},
        {"$sort": {"_id": 1}},
    ]).to_list(length=365)

    if len(docs) < 2:
        return SkuForecast(sku=sku, points=[])

    df = pd.DataFrame([{"ds": d["_id"], "y": float(d["revenue"])} for d in docs])
    df["ds"] = pd.to_datetime(df["ds"])

    points = await asyncio.to_thread(_fit_and_predict, df, horizon_days)
    return SkuForecast(sku=sku, points=points)


def _fit_and_predict(df: pd.DataFrame, horizon_days: int) -> list[ForecastPoint]:
    """Holt-Winters exponential smoothing with Prophet as optional upgrade."""
    try:
        return _prophet_forecast(df, horizon_days)
    except Exception:
        pass
    return _holtwinters_forecast(df, horizon_days)


def _prophet_forecast(df: pd.DataFrame, horizon_days: int) -> list[ForecastPoint]:
    from prophet import Prophet  # noqa: PLC0415
    model = Prophet(yearly_seasonality=False, weekly_seasonality=True, daily_seasonality=False)
    model.fit(df)
    future = model.make_future_dataframe(periods=horizon_days)
    forecast = model.predict(future).tail(horizon_days)
    return [
        ForecastPoint(
            ds=row["ds"].strftime("%Y-%m-%d"),
            yhat=round(float(row["yhat"]), 2),
            yhat_lower=round(float(row["yhat_lower"]), 2),
            yhat_upper=round(float(row["yhat_upper"]), 2),
        )
        for _, row in forecast.iterrows()
    ]


def _holtwinters_forecast(df: pd.DataFrame, horizon_days: int) -> list[ForecastPoint]:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing  # noqa: PLC0415

    series = df.set_index("ds")["y"].asfreq("D").fillna(0)

    seasonal = "add" if len(series) >= 14 else None
    trend = "add" if len(series) >= 4 else None
    sp = 7 if seasonal else None

    model = ExponentialSmoothing(series, trend=trend, seasonal=seasonal, seasonal_periods=sp)
    fit = model.fit(optimized=True, use_brute=False)

    forecast_vals = fit.forecast(horizon_days)
    residuals = fit.resid
    std = float(residuals.std()) if len(residuals) > 1 else 0.0
    ci_width = 1.96 * std

    last_date = df["ds"].max()
    return [
        ForecastPoint(
            ds=(last_date + pd.Timedelta(days=i + 1)).strftime("%Y-%m-%d"),
            yhat=round(float(max(v, 0)), 2),
            yhat_lower=round(float(max(v - ci_width, 0)), 2),
            yhat_upper=round(float(max(v + ci_width, 0)), 2),
        )
        for i, v in enumerate(forecast_vals)
    ]
