import asyncio
from datetime import date, timedelta

from app.core.cache import FORECAST_TTL, forecast_key, get_json, set_json
from app.core.mongodb import get_mongo_db
from app.domains.forecasting.forecast_service import get_sku_forecast
from app.schemas.forecast import ForecastOut


async def get_top_skus_forecast(company_id: str, n: int = 5) -> ForecastOut:
    _key = forecast_key(company_id)
    _hit = await get_json(_key)
    if _hit:
        return ForecastOut(**_hit)

    col = get_mongo_db()["staging_sales"]
    date_from = (date.today() - timedelta(days=90)).isoformat()
    date_to = date.today().isoformat()

    sku_docs = await col.aggregate([
        {"$match": {
            "_company_id": company_id,
            "date": {"$gte": date_from, "$lte": date_to},
        }},
        {"$group": {"_id": "$sku", "revenue": {"$sum": "$revenue"}}},
        {"$sort": {"revenue": -1}},
        {"$limit": n},
    ]).to_list(length=n)

    if not sku_docs:
        return ForecastOut(forecasts=[])

    skus = [d["_id"] for d in sku_docs]
    results = await asyncio.gather(
        *[get_sku_forecast(company_id, sku) for sku in skus],
        return_exceptions=True,
    )
    forecasts = [r for r in results if not isinstance(r, Exception)]
    result = ForecastOut(forecasts=forecasts)
    await set_json(_key, result.model_dump(), FORECAST_TTL)
    return result
