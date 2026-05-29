"""Inventory overview, SKU list, and SKU detail services."""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Optional

from app.core.cache import ANALYTICS_TTL, inventory_key, get_json, set_json
from app.core.mongodb import get_mongo_db
from app.domains.inventory.abc_xyz_service import get_abc_matrix, get_xyz_matrix
from app.domains.inventory.aging_service import classify_aging_bucket, compute_doh
from app.schemas.inventory import InventoryOverviewOut, SkuListOut, SkuSummaryOut


def _health_score(doh: Optional[float], stock: float, reorder_point: float) -> float:
    """Simple 0-100 health score: penalises stockout risk and overstocking."""
    if doh is None:
        return 15.0  # no demand history → dead stock risk
    if stock < reorder_point:
        base = 30.0
    elif doh < 7:
        base = 20.0
    elif 14 <= doh <= 90:
        base = 85.0
    elif 7 <= doh < 14:
        base = 55.0
    else:
        base = 45.0  # overstock (DOH > 90)
    return base


async def get_inventory_overview(company_id: str) -> InventoryOverviewOut:
    cache_key = inventory_key("overview", company_id)
    hit = await get_json(cache_key)
    if hit:
        return InventoryOverviewOut(**hit)

    db = get_mongo_db()
    col_ops = db["staging_operations"]
    col_sales = db["staging_sales"]
    col_proc = db["staging_procurement"]

    # Step 1: get latest snapshot date
    latest_docs = await col_ops.aggregate([
        {"$match": {"_company_id": company_id}},
        {"$group": {"_id": None, "max_date": {"$max": "$date"}}},
    ]).to_list(length=1)

    if not latest_docs:
        return InventoryOverviewOut(
            total_inventory_value=0.0,
            total_skus=0,
            total_stock_units=0,
            skus_at_risk=0,
            stockout_risk_skus=0,
            dead_stock_value=0.0,
            reorder_queue_count=0,
            avg_health_score=0.0,
        )

    latest_date = latest_docs[0]["max_date"]
    date_28d = (date.today() - timedelta(days=28)).isoformat()

    # Step 2: parallel queries
    stock_docs, demand_docs, cost_docs = await asyncio.gather(
        col_ops.aggregate([
            {"$match": {"_company_id": company_id, "date": latest_date}},
            {"$group": {
                "_id": "$sku",
                "total_stock": {"$sum": "$stock_level"},
                "reorder_point": {"$avg": "$reorder_point"},
            }},
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

    total_value = 0.0
    total_stock_units = 0
    skus_at_risk = 0
    stockout_risk = 0
    dead_stock_value = 0.0
    reorder_queue = 0
    health_scores: list[float] = []

    for doc in stock_docs:
        sku = doc.get("_id")
        if not sku:
            continue
        stock = float(doc.get("total_stock", 0))
        reorder_pt = float(doc.get("reorder_point", 0))
        unit_cost = costs.get(sku, 0.0)
        sku_value = stock * unit_cost

        total_value += sku_value
        total_stock_units += int(stock)

        if stock < reorder_pt:
            skus_at_risk += 1
            reorder_queue += 1

        avg_daily = demand_28.get(sku, 0) / 28
        doh = compute_doh(stock, avg_daily)

        if doh is not None and doh < 7:
            stockout_risk += 1
        if doh is None or doh >= 180:
            dead_stock_value += sku_value

        health_scores.append(_health_score(doh, stock, reorder_pt))

    avg_health = round(sum(health_scores) / len(health_scores), 1) if health_scores else 0.0

    result = InventoryOverviewOut(
        total_inventory_value=round(total_value, 2),
        total_skus=len(stock_docs),
        total_stock_units=total_stock_units,
        skus_at_risk=skus_at_risk,
        stockout_risk_skus=stockout_risk,
        dead_stock_value=round(dead_stock_value, 2),
        reorder_queue_count=reorder_queue,
        avg_health_score=avg_health,
    )
    await set_json(cache_key, result.model_dump(), ANALYTICS_TTL)
    return result


async def get_sku_list(
    company_id: str,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
) -> SkuListOut:
    db = get_mongo_db()
    col_ops = db["staging_operations"]
    col_sales = db["staging_sales"]
    col_proc = db["staging_procurement"]

    latest_docs = await col_ops.aggregate([
        {"$match": {"_company_id": company_id}},
        {"$group": {"_id": None, "max_date": {"$max": "$date"}}},
    ]).to_list(length=1)

    if not latest_docs:
        return SkuListOut(items=[], total=0, page=page, page_size=page_size)

    latest_date = latest_docs[0]["max_date"]
    date_28d = (date.today() - timedelta(days=28)).isoformat()

    stock_docs, demand_docs, cost_docs = await asyncio.gather(
        col_ops.aggregate([
            {"$match": {"_company_id": company_id, "date": latest_date}},
            {"$group": {
                "_id": "$sku",
                "total_stock": {"$sum": "$stock_level"},
                "reorder_point": {"$avg": "$reorder_point"},
            }},
            {"$sort": {"_id": 1}},
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

    abc_result = await get_abc_matrix(company_id)
    xyz_result = await get_xyz_matrix(company_id)

    abc_map: dict[str, str] = {}
    for cls, skus in abc_result.segments.items():
        for sku in skus:
            abc_map[sku] = cls

    xyz_map: dict[str, str] = {}
    for cls, skus in xyz_result.segments.items():
        for sku in skus:
            xyz_map[sku] = cls

    costs = {d["_id"]: float(d.get("avg_cost", 0)) for d in cost_docs if d.get("_id")}
    demand_28 = {d["_id"]: float(d.get("total_qty", 0)) for d in demand_docs if d.get("_id")}

    items: list[SkuSummaryOut] = []
    for doc in stock_docs:
        sku = doc.get("_id")
        if not sku:
            continue
        if search and search.lower() not in sku.lower():
            continue
        stock = float(doc.get("total_stock", 0))
        reorder_pt = float(doc.get("reorder_point", 0))
        unit_cost = costs.get(sku, 0.0)
        avg_daily = demand_28.get(sku, 0) / 28
        doh = compute_doh(stock, avg_daily)
        items.append(SkuSummaryOut(
            sku=sku,
            current_stock=stock,
            reorder_point=reorder_pt,
            avg_unit_cost=unit_cost,
            total_value=round(stock * unit_cost, 2),
            days_on_hand=doh,
            abc_class=abc_map.get(sku),
            xyz_class=xyz_map.get(sku),
            avg_daily_demand=round(avg_daily, 2),
        ))

    total = len(items)
    start = (page - 1) * page_size
    paginated = items[start: start + page_size]

    return SkuListOut(items=paginated, total=total, page=page, page_size=page_size)
