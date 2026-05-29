"""Inventory aging analysis: days-on-hand, age buckets, dead stock."""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Optional

from app.core.cache import ANALYTICS_TTL, inventory_key, get_json, set_json
from app.core.mongodb import get_mongo_db
from app.schemas.inventory import AgingBucket, AgingOut


# ── Pure utility functions ────────────────────────────────────────────────────


def compute_doh(stock: float, avg_daily_demand: float) -> Optional[float]:
    """Days-on-hand = stock / avg_daily_demand. None when demand is zero."""
    if avg_daily_demand <= 0:
        return None
    return round(stock / avg_daily_demand, 1)


def classify_aging_bucket(doh: Optional[float]) -> str:
    """Map a DOH value to one of the 5 aging buckets."""
    if doh is None:
        return "180+d"
    if doh < 30:
        return "<30d"
    if doh < 60:
        return "30-60d"
    if doh < 90:
        return "60-90d"
    if doh < 180:
        return "90-180d"
    return "180+d"


BUCKET_ORDER = ["<30d", "30-60d", "60-90d", "90-180d", "180+d"]


# ── Async service ─────────────────────────────────────────────────────────────


async def get_aging_buckets(company_id: str) -> AgingOut:
    cache_key = inventory_key("aging", company_id)
    hit = await get_json(cache_key)
    if hit:
        return AgingOut(**hit)

    db = get_mongo_db()
    col_ops = db["staging_operations"]
    col_sales = db["staging_sales"]
    col_proc = db["staging_procurement"]

    date_28d = (date.today() - timedelta(days=28)).isoformat()

    # Latest date available
    latest_docs = await col_ops.aggregate([
        {"$match": {"_company_id": company_id}},
        {"$group": {"_id": None, "max_date": {"$max": "$date"}}},
    ]).to_list(length=1)

    if not latest_docs:
        empty = AgingOut(buckets=[], total_skus=0, total_value=0.0)
        return empty

    latest_date = latest_docs[0]["max_date"]

    # Parallel: stock on latest date + avg demand last 28d + avg unit cost
    stock_docs, demand_docs, cost_docs = await asyncio.gather(
        col_ops.aggregate([
            {"$match": {"_company_id": company_id, "date": latest_date}},
            {"$group": {"_id": "$sku", "total_stock": {"$sum": "$stock_level"}}},
        ]).to_list(length=5000),
        col_sales.aggregate([
            {"$match": {"_company_id": company_id, "date": {"$gte": date_28d}}},
            {"$group": {"_id": "$sku", "total_qty": {"$sum": "$quantity"}}},
        ]).to_list(length=5000),
        col_proc.aggregate([
            {"$match": {"_company_id": company_id}},
            {"$group": {"_id": "$sku", "avg_cost": {"$avg": "$unit_cost"}}},
        ]).to_list(length=5000),
    )

    costs = {d["_id"]: float(d.get("avg_cost", 0)) for d in cost_docs if d.get("_id")}
    demand_28 = {d["_id"]: float(d.get("total_qty", 0)) for d in demand_docs if d.get("_id")}

    bucket_data: dict[str, AgingBucket] = {
        b: AgingBucket(bucket=b, sku_count=0, total_value=0.0, skus=[])
        for b in BUCKET_ORDER
    }

    for doc in stock_docs:
        sku = doc.get("_id")
        if not sku:
            continue
        stock = float(doc.get("total_stock", 0))
        avg_daily = demand_28.get(sku, 0) / 28
        doh = compute_doh(stock, avg_daily)
        bucket = classify_aging_bucket(doh)
        unit_cost = costs.get(sku, 0.0)
        bucket_data[bucket].sku_count += 1
        bucket_data[bucket].total_value += stock * unit_cost
        bucket_data[bucket].skus.append(sku)

    buckets = [bucket_data[b] for b in BUCKET_ORDER if bucket_data[b].sku_count > 0]
    for b in buckets:
        b.total_value = round(b.total_value, 2)

    total_skus = sum(b.sku_count for b in buckets)
    total_value = sum(b.total_value for b in buckets)

    result = AgingOut(
        buckets=buckets,
        total_skus=total_skus,
        total_value=round(total_value, 2),
    )
    await set_json(cache_key, result.model_dump(), ANALYTICS_TTL * 4)  # 20 min
    return result
