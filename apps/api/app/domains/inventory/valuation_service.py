"""Inventory valuation: cost value, retail value, margin by category."""
from __future__ import annotations

import asyncio

from app.core.cache import ANALYTICS_TTL, inventory_key, get_json, set_json
from app.core.mongodb import get_mongo_db
from app.schemas.inventory import CategoryValuation, ValuationOut


async def get_valuation(company_id: str) -> ValuationOut:
    cache_key = inventory_key("valuation", company_id)
    hit = await get_json(cache_key)
    if hit:
        return ValuationOut(**hit)

    db = get_mongo_db()
    col_ops = db["staging_operations"]
    col_proc = db["staging_procurement"]
    col_sales = db["staging_sales"]

    # Latest date for stock snapshot
    latest_docs = await col_ops.aggregate([
        {"$match": {"_company_id": company_id}},
        {"$group": {"_id": None, "max_date": {"$max": "$date"}}},
    ]).to_list(length=1)

    if not latest_docs:
        empty = ValuationOut(
            total_cost_value=0.0,
            total_retail_value=0.0,
            potential_margin=0.0,
            by_category=[],
        )
        return empty

    latest_date = latest_docs[0]["max_date"]

    stock_docs, cost_docs, price_docs = await asyncio.gather(
        col_ops.aggregate([
            {"$match": {"_company_id": company_id, "date": latest_date}},
            {"$group": {"_id": "$sku", "total_stock": {"$sum": "$stock_level"}}},
        ]).to_list(length=5000),
        col_proc.aggregate([
            {"$match": {"_company_id": company_id}},
            {"$group": {
                "_id": "$sku",
                "avg_cost": {"$avg": "$unit_cost"},
                "supplier_id": {"$first": "$supplier_id"},
            }},
        ]).to_list(length=5000),
        # avg revenue per unit sold as proxy for unit price
        col_sales.aggregate([
            {"$match": {"_company_id": company_id}},
            {"$group": {
                "_id": "$sku",
                "total_revenue": {"$sum": "$revenue"},
                "total_qty": {"$sum": "$quantity"},
            }},
        ]).to_list(length=5000),
    )

    costs = {d["_id"]: float(d.get("avg_cost", 0)) for d in cost_docs if d.get("_id")}
    # Derive a rough "supplier_id→category" using supplier prefix heuristic
    cat_by_supplier = {d["_id"]: str(d.get("supplier_id", "Unknown"))[:3].upper() for d in cost_docs if d.get("_id")}

    prices: dict[str, float] = {}
    for d in price_docs:
        sku = d.get("_id")
        if not sku:
            continue
        qty = float(d.get("total_qty", 0))
        rev = float(d.get("total_revenue", 0))
        prices[sku] = rev / qty if qty > 0 else 0.0

    category_buckets: dict[str, dict] = {}
    total_cost = 0.0
    total_retail = 0.0

    for doc in stock_docs:
        sku = doc.get("_id")
        if not sku:
            continue
        stock = float(doc.get("total_stock", 0))
        unit_cost = costs.get(sku, 0.0)
        unit_price = prices.get(sku, 0.0)

        sku_cost_val = stock * unit_cost
        sku_retail_val = stock * unit_price
        total_cost += sku_cost_val
        total_retail += sku_retail_val

        # Use first 3 chars of SKU as a rough category proxy when no real category
        cat = sku.split("-")[0] if "-" in sku else sku[:3]
        if cat not in category_buckets:
            category_buckets[cat] = {"cost_value": 0.0, "retail_value": 0.0, "sku_count": 0}
        category_buckets[cat]["cost_value"] += sku_cost_val
        category_buckets[cat]["retail_value"] += sku_retail_val
        category_buckets[cat]["sku_count"] += 1

    by_category = [
        CategoryValuation(
            category=cat,
            cost_value=round(vals["cost_value"], 2),
            retail_value=round(vals["retail_value"], 2),
            sku_count=vals["sku_count"],
        )
        for cat, vals in sorted(category_buckets.items(), key=lambda x: -x[1]["cost_value"])
    ]

    potential_margin = (
        round((total_retail - total_cost) / total_retail * 100, 1)
        if total_retail > 0 else 0.0
    )

    result = ValuationOut(
        total_cost_value=round(total_cost, 2),
        total_retail_value=round(total_retail, 2),
        potential_margin=potential_margin,
        by_category=by_category,
    )
    await set_json(cache_key, result.model_dump(), ANALYTICS_TTL * 4)
    return result
