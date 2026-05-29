from datetime import date, timedelta
from typing import Optional

from app.core.cache import ANALYTICS_TTL, analytics_key, get_json, set_json
from app.core.mongodb import get_mongo_db
from app.domains.analytics.utils import compute_compare_period, parse_dims, pct_delta
from app.schemas.analytics import (
    DailyRevenue,
    RegionRevenue,
    SalesKpisOut,
    SkuRevenue,
)


async def get_sales_kpis(
    company_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    compare_to: Optional[str] = None,
    dims: Optional[str] = None,
) -> SalesKpisOut:
    if not date_from:
        date_from = (date.today() - timedelta(days=90)).isoformat()
    if not date_to:
        date_to = date.today().isoformat()

    # Cache key includes compare_to/dims so different requests stay isolated
    _key = analytics_key("sales", company_id, date_from, date_to)
    if compare_to or dims:
        _key += f":{compare_to or ''}:{dims or ''}"

    _hit = await get_json(_key)
    if _hit:
        return SalesKpisOut(**_hit)

    col = get_mongo_db()["staging_sales"]

    dim_filter = parse_dims(dims)
    match: dict = {
        "_company_id": company_id,
        "date": {"$gte": date_from, "$lte": date_to},
        **dim_filter,
    }

    # ── Total KPIs ────────────────────────────────────────────────────────────
    totals_docs = await col.aggregate([
        {"$match": match},
        {"$group": {
            "_id": None,
            "total_revenue": {"$sum": "$revenue"},
            "total_units": {"$sum": "$quantity"},
            "count": {"$sum": 1},
        }},
    ]).to_list(length=1)

    totals = totals_docs[0] if totals_docs else {}
    total_revenue: float = float(totals.get("total_revenue", 0.0))
    total_units: int = int(totals.get("total_units", 0))
    count: int = int(totals.get("count", 0))
    aov: float = round(total_revenue / count, 2) if count > 0 else 0.0

    # ── Top 10 SKUs ───────────────────────────────────────────────────────────
    sku_docs = await col.aggregate([
        {"$match": match},
        {"$group": {"_id": "$sku", "revenue": {"$sum": "$revenue"}}},
        {"$sort": {"revenue": -1}},
        {"$limit": 10},
    ]).to_list(length=10)
    top_skus = [SkuRevenue(sku=d["_id"], revenue=round(float(d["revenue"]), 2)) for d in sku_docs]

    # ── Revenue by region ─────────────────────────────────────────────────────
    region_docs = await col.aggregate([
        {"$match": match},
        {"$group": {"_id": "$region", "revenue": {"$sum": "$revenue"}}},
        {"$sort": {"revenue": -1}},
    ]).to_list(length=50)
    revenue_by_region = [
        RegionRevenue(region=d["_id"] or "Unknown", revenue=round(float(d["revenue"]), 2))
        for d in region_docs
    ]

    # ── Daily revenue time-series ─────────────────────────────────────────────
    daily_docs = await col.aggregate([
        {"$match": match},
        {"$group": {"_id": "$date", "revenue": {"$sum": "$revenue"}}},
        {"$sort": {"_id": 1}},
    ]).to_list(length=365)
    daily_revenue = [
        DailyRevenue(date=d["_id"], revenue=round(float(d["revenue"]), 2))
        for d in daily_docs
    ]

    # ── Compare-period deltas ─────────────────────────────────────────────────
    deltas: dict[str, float] | None = None
    if compare_to:
        comp = compute_compare_period(date_from, date_to, compare_to)
        if comp:
            prev_from, prev_to = comp
            prev_match: dict = {
                "_company_id": company_id,
                "date": {"$gte": prev_from, "$lte": prev_to},
                **dim_filter,
            }
            prev_docs = await col.aggregate([
                {"$match": prev_match},
                {"$group": {
                    "_id": None,
                    "total_revenue": {"$sum": "$revenue"},
                    "total_units": {"$sum": "$quantity"},
                    "count": {"$sum": 1},
                }},
            ]).to_list(length=1)
            prev = prev_docs[0] if prev_docs else {}
            prev_revenue = float(prev.get("total_revenue", 0.0))
            prev_units = int(prev.get("total_units", 0))
            prev_count = int(prev.get("count", 0))
            prev_aov = round(prev_revenue / prev_count, 2) if prev_count > 0 else 0.0
            deltas = {}
            d = pct_delta(round(total_revenue, 2), prev_revenue)
            if d is not None:
                deltas["total_revenue"] = d
            d = pct_delta(float(total_units), float(prev_units))
            if d is not None:
                deltas["total_units"] = d
            d = pct_delta(aov, prev_aov)
            if d is not None:
                deltas["aov"] = d

    result = SalesKpisOut(
        total_revenue=round(total_revenue, 2),
        total_units=total_units,
        aov=aov,
        top_sku=top_skus[0].sku if top_skus else None,
        top_skus=top_skus,
        revenue_by_region=revenue_by_region,
        daily_revenue=daily_revenue,
        deltas=deltas,
    )
    await set_json(_key, result.model_dump(), ANALYTICS_TTL)
    return result
