"""Reorder intelligence: EOQ, safety stock, reorder point, and reorder queue."""
from __future__ import annotations

import asyncio
import hashlib
import math
from datetime import date, timedelta
from typing import Optional

from app.core.cache import ANALYTICS_TTL, get_json, inventory_key, set_json
from app.core.mongodb import get_mongo_db
from app.schemas.inventory import ReorderItem, ReorderQueueOut


# ── Service level → Z-score lookup (avoids scipy dep) ────────────────────────

_Z_SCORES: dict[float, float] = {
    0.90: 1.28,
    0.95: 1.65,
    0.98: 2.05,
    0.99: 2.33,
}


def compute_eoq(
    annual_demand: float,
    ordering_cost: float = 25.0,
    holding_cost_per_unit: float = 0.0,
    unit_cost: float = 0.0,
    holding_pct: float = 0.25,
) -> float:
    """Economic Order Quantity: sqrt(2 × D × S / H).

    holding_cost_per_unit defaults to 25% of unit_cost (if unit_cost > 0).
    """
    if annual_demand <= 0:
        return 0.0
    h = holding_cost_per_unit if holding_cost_per_unit > 0 else unit_cost * holding_pct
    if h <= 0:
        h = 1.0  # Fallback: $1/unit/year holding cost
    return round(math.sqrt(2 * annual_demand * ordering_cost / h), 1)


def compute_safety_stock(
    demand_std: float,
    lead_time_days: float,
    service_level: float = 0.95,
) -> float:
    """Safety stock: Z × σ_demand × sqrt(lead_time_days)."""
    if demand_std <= 0 or lead_time_days <= 0:
        return 0.0
    z = _Z_SCORES.get(service_level, 1.65)
    return round(z * demand_std * math.sqrt(lead_time_days), 1)


def compute_reorder_point(
    avg_daily_demand: float,
    lead_time_days: float,
    safety_stock: float,
) -> float:
    """Reorder point: avg_daily_demand × lead_time + safety_stock."""
    return round(avg_daily_demand * lead_time_days + safety_stock, 1)


def reorder_item_id(company_id: str, sku: str) -> str:
    """Stable hash ID for a reorder queue item."""
    return hashlib.sha256(f"{company_id}:{sku}".encode()).hexdigest()[:16]


# ── Async queue service ───────────────────────────────────────────────────────


async def get_reorder_queue(company_id: str) -> ReorderQueueOut:
    """Return ranked reorder recommendations for all SKUs below reorder point."""
    cache_key = inventory_key("reorder-queue", company_id)
    hit = await get_json(cache_key)
    if hit:
        return ReorderQueueOut(**hit)

    db = get_mongo_db()
    col_ops = db["staging_operations"]
    col_sales = db["staging_sales"]
    col_proc = db["staging_procurement"]

    # Latest snapshot date
    latest_docs = await col_ops.aggregate([
        {"$match": {"_company_id": company_id}},
        {"$group": {"_id": None, "max_date": {"$max": "$date"}}},
    ]).to_list(length=1)

    if not latest_docs:
        return ReorderQueueOut(items=[], total=0)

    latest_date = latest_docs[0]["max_date"]
    date_28d = (date.today() - timedelta(days=28)).isoformat()
    date_90d = (date.today() - timedelta(days=90)).isoformat()

    # Parallel queries: stock, demand, cost, lead_times
    stock_docs, demand_28d_docs, demand_90d_docs, cost_docs = await asyncio.gather(
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
        col_sales.aggregate([
            {"$match": {"_company_id": company_id, "date": {"$gte": date_90d}}},
            {"$group": {
                "_id": "$sku",
                "total_qty": {"$sum": "$quantity"},
                "count_days": {"$addToSet": "$date"},
            }},
        ]).to_list(length=5000),
        col_proc.aggregate([
            {"$match": {"_company_id": company_id}},
            {"$group": {
                "_id": "$sku",
                "avg_cost": {"$avg": "$unit_cost"},
                "avg_lead": {"$avg": "$lead_time_days"},
            }},
        ]).to_list(length=5000),
    )

    demand_28 = {d["_id"]: float(d.get("total_qty", 0)) for d in demand_28d_docs if d.get("_id")}
    demand_90 = {d["_id"]: float(d.get("total_qty", 0)) for d in demand_90d_docs if d.get("_id")}
    count_90 = {d["_id"]: len(d.get("count_days", [])) for d in demand_90d_docs if d.get("_id")}
    costs = {d["_id"]: float(d.get("avg_cost", 0)) for d in cost_docs if d.get("_id")}
    lead_days_map = {
        d["_id"]: float(d.get("avg_lead") or 14)
        for d in cost_docs if d.get("_id")
    }

    items: list[ReorderItem] = []

    for doc in stock_docs:
        sku = doc.get("_id")
        if not sku:
            continue
        stock = float(doc.get("total_stock", 0))
        db_reorder_pt = float(doc.get("reorder_point", 0))
        unit_cost = costs.get(sku, 0.0)
        lead_time = lead_days_map.get(sku, 14.0)

        # Demand stats
        qty_28 = demand_28.get(sku, 0.0)
        qty_90 = demand_90.get(sku, 0.0)
        n_days_90 = max(count_90.get(sku, 1), 1)

        avg_daily_28 = qty_28 / 28 if qty_28 > 0 else 0.0
        avg_daily_90 = qty_90 / n_days_90 if qty_90 > 0 else 0.0

        # Use 28d demand for recency, fallback to 90d
        avg_daily = avg_daily_28 if avg_daily_28 > 0 else avg_daily_90

        # Estimate demand std from difference between 28d and 90d rates
        demand_std = abs(avg_daily_28 - avg_daily_90) if avg_daily_28 > 0 and avg_daily_90 > 0 else avg_daily * 0.3

        safety_stock = compute_safety_stock(demand_std, lead_time)
        reorder_point = compute_reorder_point(avg_daily, lead_time, safety_stock)

        # Use the higher of computed vs DB reorder point
        effective_reorder_pt = max(reorder_point, db_reorder_pt)

        # Only add to queue if below reorder point
        if stock >= effective_reorder_pt:
            continue

        annual_demand = avg_daily * 365 if avg_daily > 0 else 0
        eoq = compute_eoq(annual_demand, ordering_cost=25.0, unit_cost=unit_cost)
        recommended_qty = max(eoq, effective_reorder_pt - stock + safety_stock)

        days_until_stockout = round(stock / avg_daily, 1) if avg_daily > 0 else None

        # Priority classification
        if days_until_stockout is not None and days_until_stockout < 7:
            priority = "critical"
        elif days_until_stockout is not None and days_until_stockout < 14:
            priority = "high"
        elif stock <= 0:
            priority = "critical"
        else:
            priority = "medium"

        items.append(ReorderItem(
            id=reorder_item_id(company_id, sku),
            sku=sku,
            current_stock=round(stock, 1),
            reorder_point=round(effective_reorder_pt, 1),
            safety_stock=round(safety_stock, 1),
            eoq=round(eoq, 1),
            avg_daily_demand=round(avg_daily, 3),
            lead_time_days=round(lead_time, 1),
            days_until_stockout=days_until_stockout,
            priority=priority,
            recommended_order_qty=round(recommended_qty, 1),
            estimated_cost=round(recommended_qty * unit_cost, 2),
        ))

    # Sort: critical first, then by days_until_stockout asc
    priority_order = {"critical": 0, "high": 1, "medium": 2}
    items.sort(key=lambda x: (priority_order[x.priority], x.days_until_stockout or 9999))

    result = ReorderQueueOut(items=items, total=len(items))
    await set_json(cache_key, result.model_dump(), ANALYTICS_TTL)
    return result


async def get_understock(company_id: str) -> dict:
    """SKUs below safety stock + projected stock-out days."""
    cache_key = inventory_key("understock", company_id)
    hit = await get_json(cache_key)
    if hit:
        return hit

    queue = await get_reorder_queue(company_id)
    understock_items = [
        {
            "sku": item.sku,
            "current_stock": item.current_stock,
            "reorder_point": item.reorder_point,
            "days_until_stockout": item.days_until_stockout,
            "shortage_units": round(max(0, item.reorder_point - item.current_stock), 1),
            "priority": item.priority,
        }
        for item in queue.items
    ]

    result = {"items": understock_items, "total": len(understock_items)}
    await set_json(cache_key, result, ANALYTICS_TTL)
    return result


async def get_dead_stock(company_id: str, days_threshold: int = 90) -> dict:
    """SKUs not sold in N days, ranked by tied-up capital."""
    cache_key = inventory_key(f"dead-stock-{days_threshold}", company_id)
    hit = await get_json(cache_key)
    if hit:
        return hit

    db = get_mongo_db()
    col_ops = db["staging_operations"]
    col_sales = db["staging_sales"]
    col_proc = db["staging_procurement"]

    threshold_date = (date.today() - timedelta(days=days_threshold)).isoformat()
    latest_docs = await col_ops.aggregate([
        {"$match": {"_company_id": company_id}},
        {"$group": {"_id": None, "max_date": {"$max": "$date"}}},
    ]).to_list(length=1)

    if not latest_docs:
        return {"items": [], "total_tied_up_value": 0.0, "total": 0}

    latest_date = latest_docs[0]["max_date"]

    stock_docs, recent_sales_docs, cost_docs = await asyncio.gather(
        col_ops.aggregate([
            {"$match": {"_company_id": company_id, "date": latest_date}},
            {"$group": {"_id": "$sku", "total_stock": {"$sum": "$stock_level"}}},
        ]).to_list(length=5000),
        col_sales.aggregate([
            {"$match": {"_company_id": company_id, "date": {"$gte": threshold_date}}},
            {"$group": {"_id": "$sku", "recent_qty": {"$sum": "$quantity"}}},
        ]).to_list(length=5000),
        col_proc.aggregate([
            {"$match": {"_company_id": company_id}},
            {"$group": {"_id": "$sku", "avg_cost": {"$avg": "$unit_cost"}}},
        ]).to_list(length=5000),
    )

    recent_sold = {d["_id"] for d in recent_sales_docs if d.get("_id") and d.get("recent_qty", 0) > 0}
    costs = {d["_id"]: float(d.get("avg_cost", 0)) for d in cost_docs if d.get("_id")}

    items = []
    total_value = 0.0

    for doc in stock_docs:
        sku = doc.get("_id")
        if not sku or sku in recent_sold:
            continue
        stock = float(doc.get("total_stock", 0))
        if stock <= 0:
            continue
        unit_cost = costs.get(sku, 0.0)
        tied_up = round(stock * unit_cost, 2)
        total_value += tied_up
        items.append({
            "sku": sku,
            "current_stock": round(stock, 1),
            "last_sold_days_ago": days_threshold,  # At least this many days ago
            "tied_up_value": tied_up,
            "doh": None,  # No demand → undefined DOH
        })

    items.sort(key=lambda x: x["tied_up_value"], reverse=True)
    result = {
        "items": items,
        "total_tied_up_value": round(total_value, 2),
        "total": len(items),
    }
    await set_json(cache_key, result, ANALYTICS_TTL)
    return result


async def get_overstock(company_id: str, target_doh: float = 90.0) -> dict:
    """SKUs with DOH significantly above target."""
    cache_key = inventory_key(f"overstock-{int(target_doh)}", company_id)
    hit = await get_json(cache_key)
    if hit:
        return hit

    db = get_mongo_db()
    col_ops = db["staging_operations"]
    col_sales = db["staging_sales"]
    col_proc = db["staging_procurement"]

    latest_docs = await col_ops.aggregate([
        {"$match": {"_company_id": company_id}},
        {"$group": {"_id": None, "max_date": {"$max": "$date"}}},
    ]).to_list(length=1)

    if not latest_docs:
        return {"items": [], "total_excess_value": 0.0, "total": 0}

    latest_date = latest_docs[0]["max_date"]
    date_28d = (date.today() - timedelta(days=28)).isoformat()

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

    demand = {d["_id"]: float(d.get("total_qty", 0)) for d in demand_docs if d.get("_id")}
    costs = {d["_id"]: float(d.get("avg_cost", 0)) for d in cost_docs if d.get("_id")}

    items = []
    total_excess_value = 0.0

    for doc in stock_docs:
        sku = doc.get("_id")
        if not sku:
            continue
        stock = float(doc.get("total_stock", 0))
        if stock <= 0:
            continue
        avg_daily = demand.get(sku, 0.0) / 28
        if avg_daily <= 0:
            continue
        doh = stock / avg_daily
        if doh <= target_doh:
            continue

        unit_cost = costs.get(sku, 0.0)
        excess_units = (doh - target_doh) * avg_daily
        excess_value = round(excess_units * unit_cost, 2)
        total_excess_value += excess_value

        items.append({
            "sku": sku,
            "current_stock": round(stock, 1),
            "doh": round(doh, 1),
            "excess_units": round(excess_units, 1),
            "excess_value": excess_value,
            "target_doh": target_doh,
        })

    items.sort(key=lambda x: x["excess_value"], reverse=True)
    result = {
        "items": items,
        "total_excess_value": round(total_excess_value, 2),
        "total": len(items),
    }
    await set_json(cache_key, result, ANALYTICS_TTL)
    return result
