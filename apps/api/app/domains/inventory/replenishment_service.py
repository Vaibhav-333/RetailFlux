"""Supplier-aware purchase order draft suggestions (Auto-Replenishment, §4.3 start)."""
from __future__ import annotations

import asyncio
from datetime import date, timedelta

from app.core.cache import ANALYTICS_TTL, get_json, inventory_key, set_json
from app.core.mongodb import get_mongo_db
from app.domains.inventory.reorder_service import get_reorder_queue
from app.schemas.inventory import PoLineItem, ReplenishmentOut, SupplierPoDraft


async def get_replenishment_suggestions(company_id: str) -> ReplenishmentOut:
    """Group reorder items by (inferred) supplier to create PO drafts."""
    cache_key = inventory_key("replenishment", company_id)
    hit = await get_json(cache_key)
    if hit:
        return ReplenishmentOut(**hit)

    # Get reorder queue (already cached)
    queue = await get_reorder_queue(company_id)
    if not queue.items:
        result = ReplenishmentOut(po_drafts=[], total_suggested_cost=0.0)
        await set_json(cache_key, result.model_dump(), ANALYTICS_TTL)
        return result

    # Group by supplier using staging_procurement supplier data
    db = get_mongo_db()
    col_proc = db["staging_procurement"]

    # Get supplier info for the SKUs in the reorder queue
    reorder_skus = [item.sku for item in queue.items]
    supplier_docs = await col_proc.aggregate([
        {"$match": {"_company_id": company_id, "sku": {"$in": reorder_skus}}},
        {"$group": {
            "_id": "$sku",
            "supplier": {"$last": "$supplier"},
            "avg_lead": {"$avg": "$lead_time_days"},
        }},
    ]).to_list(length=5000)

    supplier_map = {d["_id"]: d.get("supplier", "Unknown Supplier") for d in supplier_docs}
    lead_map = {d["_id"]: float(d.get("avg_lead") or 14) for d in supplier_docs}

    # Group reorder items by supplier
    by_supplier: dict[str, list] = {}
    for item in queue.items:
        supplier_name = supplier_map.get(item.sku, "Default Supplier")
        if supplier_name not in by_supplier:
            by_supplier[supplier_name] = []
        by_supplier[supplier_name].append(item)

    today = date.today()
    po_drafts: list[SupplierPoDraft] = []
    total_cost = 0.0

    for supplier_name, items in by_supplier.items():
        avg_lead = max(lead_map.get(item.sku, 14) for item in items)
        expected_delivery = (today + timedelta(days=int(avg_lead))).isoformat()
        lines = [
            PoLineItem(
                sku=item.sku,
                quantity=item.recommended_order_qty,
                unit_cost=round(item.estimated_cost / item.recommended_order_qty, 4)
                if item.recommended_order_qty > 0 else 0.0,
                line_total=item.estimated_cost,
            )
            for item in items
        ]
        draft_total = sum(ln.line_total for ln in lines)
        total_cost += draft_total
        po_drafts.append(SupplierPoDraft(
            supplier_name=supplier_name,
            lines=lines,
            total_cost=round(draft_total, 2),
            lead_time_days=int(avg_lead),
            expected_delivery=expected_delivery,
            sku_count=len(lines),
            priority="critical" if any(i.priority == "critical" for i in items) else "high",
        ))

    # Sort by most urgent first
    po_drafts.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2}.get(x.priority, 3))

    result = ReplenishmentOut(
        po_drafts=po_drafts,
        total_suggested_cost=round(total_cost, 2),
    )
    await set_json(cache_key, result.model_dump(), ANALYTICS_TTL)
    return result


async def get_transfer_suggestions(company_id: str) -> dict:
    """Suggest inter-warehouse transfers to balance demand vs stock."""
    cache_key = inventory_key("transfer-suggestions", company_id)
    hit = await get_json(cache_key)
    if hit:
        return hit

    db = get_mongo_db()
    col_ops = db["staging_operations"]
    col_sales = db["staging_sales"]

    latest_docs = await col_ops.aggregate([
        {"$match": {"_company_id": company_id}},
        {"$group": {"_id": None, "max_date": {"$max": "$date"}}},
    ]).to_list(length=1)

    if not latest_docs:
        return {"suggestions": [], "total": 0}

    latest_date = latest_docs[0]["max_date"]
    date_28d = (date.today() - timedelta(days=28)).isoformat()

    # Stock per warehouse per SKU
    warehouse_stock_docs, demand_docs = await asyncio.gather(
        col_ops.aggregate([
            {"$match": {"_company_id": company_id, "date": latest_date}},
            {"$group": {
                "_id": {"sku": "$sku", "warehouse": "$warehouse"},
                "stock": {"$sum": "$stock_level"},
            }},
        ]).to_list(length=20000),
        col_sales.aggregate([
            {"$match": {"_company_id": company_id, "date": {"$gte": date_28d}}},
            {"$group": {
                "_id": {"sku": "$sku", "region": "$region"},
                "qty": {"$sum": "$quantity"},
            }},
        ]).to_list(length=20000),
    )

    # Build warehouse×SKU stock map
    wh_stock: dict[str, dict[str, float]] = {}  # sku → {warehouse → stock}
    for doc in warehouse_stock_docs:
        key = doc.get("_id", {})
        sku = key.get("sku", "")
        wh = key.get("warehouse", "WH-1")
        if sku:
            wh_stock.setdefault(sku, {})[wh] = float(doc.get("stock", 0))

    suggestions = []
    for sku, wh_data in wh_stock.items():
        if len(wh_data) < 2:
            continue
        stocks = list(wh_data.values())
        warehouses = list(wh_data.keys())
        avg = sum(stocks) / len(stocks)
        if avg == 0:
            continue

        max_wh = warehouses[stocks.index(max(stocks))]
        min_wh = warehouses[stocks.index(min(stocks))]
        max_stock = max(stocks)
        min_stock = min(stocks)

        # Only suggest if imbalance is significant (>50% above average)
        if max_stock < avg * 1.5 or min_stock > avg * 0.5:
            continue

        transfer_qty = round((max_stock - avg) * 0.5, 1)
        if transfer_qty < 1:
            continue

        suggestions.append({
            "sku": sku,
            "from_warehouse": max_wh,
            "to_warehouse": min_wh,
            "quantity": transfer_qty,
            "reason": f"Rebalance: {max_wh} has {max_stock:.0f} units vs {min_wh} with {min_stock:.0f}",
            "value": 0.0,  # Would enrich with unit cost
        })

    suggestions.sort(key=lambda x: x["quantity"], reverse=True)
    result = {"suggestions": suggestions[:20], "total": len(suggestions)}
    await set_json(cache_key, result, ANALYTICS_TTL)
    return result


async def get_heatmap(company_id: str) -> dict:
    """Warehouse × Category stock health heatmap."""
    cache_key = inventory_key("heatmap", company_id)
    hit = await get_json(cache_key)
    if hit:
        return hit

    db = get_mongo_db()
    col_ops = db["staging_operations"]
    col_proc = db["staging_procurement"]

    latest_docs = await col_ops.aggregate([
        {"$match": {"_company_id": company_id}},
        {"$group": {"_id": None, "max_date": {"$max": "$date"}}},
    ]).to_list(length=1)

    if not latest_docs:
        return {"cells": [], "warehouses": [], "categories": []}

    latest_date = latest_docs[0]["max_date"]

    stock_docs, cost_docs = await asyncio.gather(
        col_ops.aggregate([
            {"$match": {"_company_id": company_id, "date": latest_date}},
            {"$group": {
                "_id": {"sku": "$sku", "warehouse": "$warehouse"},
                "stock": {"$sum": "$stock_level"},
                "reorder_point": {"$avg": "$reorder_point"},
            }},
        ]).to_list(length=20000),
        col_proc.aggregate([
            {"$match": {"_company_id": company_id}},
            {"$group": {
                "_id": "$sku",
                "avg_cost": {"$avg": "$unit_cost"},
                "category": {"$last": "$category"},
            }},
        ]).to_list(length=5000),
    )

    category_map = {d["_id"]: d.get("category", "General") or "General" for d in cost_docs}
    cost_map = {d["_id"]: float(d.get("avg_cost", 0)) for d in cost_docs}

    # Aggregate by (warehouse, category)
    cells_acc: dict[tuple, dict] = {}
    warehouses_set: set[str] = set()
    categories_set: set[str] = set()

    for doc in stock_docs:
        key = doc.get("_id", {})
        sku = key.get("sku", "")
        wh = key.get("warehouse", "WH-1") or "WH-1"
        if not sku:
            continue
        stock = float(doc.get("stock", 0))
        reorder_pt = float(doc.get("reorder_point", 0))
        cat = category_map.get(sku, "General")
        unit_cost = cost_map.get(sku, 0.0)

        cell_key = (wh, cat)
        if cell_key not in cells_acc:
            cells_acc[cell_key] = {"sku_count": 0, "total_value": 0.0, "below_reorder": 0}
        cells_acc[cell_key]["sku_count"] += 1
        cells_acc[cell_key]["total_value"] += stock * unit_cost
        if stock < reorder_pt:
            cells_acc[cell_key]["below_reorder"] += 1

        warehouses_set.add(wh)
        categories_set.add(cat)

    cells = []
    for (wh, cat), data in cells_acc.items():
        count = data["sku_count"]
        below = data["below_reorder"]
        # Health = % NOT below reorder
        health = round(100 * (1 - below / count), 1) if count > 0 else 100.0
        cells.append({
            "warehouse": wh,
            "category": cat,
            "health_score": health,
            "sku_count": count,
            "total_value": round(data["total_value"], 2),
        })

    result = {
        "cells": cells,
        "warehouses": sorted(warehouses_set),
        "categories": sorted(categories_set),
    }
    await set_json(cache_key, result, ANALYTICS_TTL)
    return result
