"""Inventory velocity: sell-through, turnover, fast/slow movers."""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Optional

from app.core.cache import ANALYTICS_TTL, analytics_key, get_json, set_json
from app.core.mongodb import get_mongo_db
from app.schemas.inventory import SkuVelocity, VelocityOut


async def get_velocity(
    company_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> VelocityOut:
    if not date_from:
        date_from = (date.today() - timedelta(days=90)).isoformat()
    if not date_to:
        date_to = date.today().isoformat()

    cache_key = analytics_key("inventory_velocity", company_id, date_from, date_to)
    hit = await get_json(cache_key)
    if hit:
        return VelocityOut(**hit)

    db = get_mongo_db()
    col_sales = db["staging_sales"]
    col_ops = db["staging_operations"]
    col_proc = db["staging_procurement"]

    # Latest snapshot date
    latest_docs = await col_ops.aggregate([
        {"$match": {"_company_id": company_id}},
        {"$group": {"_id": None, "max_date": {"$max": "$date"}}},
    ]).to_list(length=1)

    if not latest_docs:
        return VelocityOut(fast_movers=[], slow_movers=[], avg_sell_through=0.0, total_skus_analyzed=0)

    latest_date = latest_docs[0]["max_date"]

    sales_docs, stock_docs, cost_docs = await asyncio.gather(
        col_sales.aggregate([
            {"$match": {"_company_id": company_id, "date": {"$gte": date_from, "$lte": date_to}}},
            {"$group": {
                "_id": "$sku",
                "units_sold": {"$sum": "$quantity"},
                "revenue": {"$sum": "$revenue"},
            }},
            {"$sort": {"units_sold": -1}},
        ]).to_list(length=5000),
        col_ops.aggregate([
            {"$match": {"_company_id": company_id, "date": latest_date}},
            {"$group": {"_id": "$sku", "total_stock": {"$sum": "$stock_level"}}},
        ]).to_list(length=5000),
        col_proc.aggregate([
            {"$match": {"_company_id": company_id}},
            {"$group": {"_id": "$sku", "avg_cost": {"$avg": "$unit_cost"}}},
        ]).to_list(length=5000),
    )

    stocks = {d["_id"]: float(d.get("total_stock", 0)) for d in stock_docs if d.get("_id")}
    costs = {d["_id"]: float(d.get("avg_cost", 0)) for d in cost_docs if d.get("_id")}

    sku_velocities: list[SkuVelocity] = []
    for doc in sales_docs:
        sku = doc.get("_id")
        if not sku:
            continue
        units_sold = float(doc.get("units_sold", 0))
        revenue = float(doc.get("revenue", 0))
        current_stock = stocks.get(sku, 0.0)
        avg_unit_cost = costs.get(sku, 0.0)
        opening_stock = units_sold + current_stock
        sell_through = units_sold / opening_stock if opening_stock > 0 else 0.0
        sku_velocities.append(SkuVelocity(
            sku=sku,
            units_sold=units_sold,
            current_stock=current_stock,
            sell_through=round(sell_through, 4),
            avg_unit_cost=avg_unit_cost,
            revenue=revenue,
        ))

    sku_velocities.sort(key=lambda s: s.sell_through, reverse=True)
    midpoint = max(1, len(sku_velocities) // 2)
    fast_movers = sku_velocities[:min(10, midpoint)]
    slow_movers = sku_velocities[max(0, len(sku_velocities) - 10):][::-1]

    avg_sell_through = (
        round(sum(s.sell_through for s in sku_velocities) / len(sku_velocities), 4)
        if sku_velocities else 0.0
    )

    result = VelocityOut(
        fast_movers=fast_movers,
        slow_movers=slow_movers,
        avg_sell_through=avg_sell_through,
        total_skus_analyzed=len(sku_velocities),
    )
    await set_json(cache_key, result.model_dump(), ANALYTICS_TTL * 4)
    return result
