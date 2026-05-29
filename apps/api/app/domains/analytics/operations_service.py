from datetime import date, timedelta
from typing import Optional

from app.core.cache import ANALYTICS_TTL, analytics_key, get_json, set_json
from app.core.mongodb import get_mongo_db
from app.domains.analytics.utils import compute_compare_period, parse_dims, pct_delta
from app.schemas.analytics import (
    DailyStockLevel,
    LowStockSku,
    OperationsKpisOut,
    WarehouseStock,
)


async def get_operations_kpis(
    company_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    compare_to: Optional[str] = None,
    dims: Optional[str] = None,
) -> OperationsKpisOut:
    if not date_from:
        date_from = (date.today() - timedelta(days=90)).isoformat()
    if not date_to:
        date_to = date.today().isoformat()

    _key = analytics_key("operations", company_id, date_from, date_to)
    if compare_to or dims:
        _key += f":{compare_to or ''}:{dims or ''}"

    _hit = await get_json(_key)
    if _hit:
        return OperationsKpisOut(**_hit)

    col = get_mongo_db()["staging_operations"]

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
            "total_stock_units": {"$sum": "$stock_level"},
            "skus": {"$addToSet": "$sku"},
            "warehouses": {"$addToSet": "$warehouse"},
        }},
        {"$project": {
            "total_stock_units": 1,
            "total_skus": {"$size": "$skus"},
            "total_warehouses": {"$size": "$warehouses"},
        }},
    ]).to_list(length=1)

    totals = totals_docs[0] if totals_docs else {}
    total_skus: int = int(totals.get("total_skus", 0))
    total_stock_units: int = int(totals.get("total_stock_units", 0))
    active_warehouses: int = int(totals.get("total_warehouses", 0))

    # ── SKUs currently below reorder point ────────────────────────────────────
    below_docs = await col.aggregate([
        {"$match": {**match, "$expr": {"$lt": ["$stock_level", "$reorder_point"]}}},
        {"$group": {"_id": "$sku"}},
        {"$count": "total"},
    ]).to_list(length=1)
    skus_below_reorder: int = int(below_docs[0]["total"]) if below_docs else 0

    # ── Stock level by warehouse ───────────────────────────────────────────────
    wh_docs = await col.aggregate([
        {"$match": match},
        {"$group": {"_id": "$warehouse", "stock_level": {"$sum": "$stock_level"}}},
        {"$sort": {"stock_level": -1}},
    ]).to_list(length=50)
    stock_by_warehouse = [
        WarehouseStock(warehouse=d["_id"] or "Unknown", stock_level=int(d["stock_level"]))
        for d in wh_docs
    ]

    # ── Top 10 low-stock SKUs (avg stock level ascending) ─────────────────────
    low_docs = await col.aggregate([
        {"$match": match},
        {"$group": {
            "_id": "$sku",
            "avg_stock": {"$avg": "$stock_level"},
            "reorder_point": {"$first": "$reorder_point"},
        }},
        {"$sort": {"avg_stock": 1}},
        {"$limit": 10},
    ]).to_list(length=10)
    low_stock_skus = [
        LowStockSku(
            sku=d["_id"],
            stock_level=round(float(d["avg_stock"]), 1),
            reorder_point=int(d["reorder_point"]),
        )
        for d in low_docs
    ]

    # ── Daily avg stock level time-series ─────────────────────────────────────
    daily_docs = await col.aggregate([
        {"$match": match},
        {"$group": {"_id": "$date", "avg_stock_level": {"$avg": "$stock_level"}}},
        {"$sort": {"_id": 1}},
    ]).to_list(length=365)
    daily_stock_level = [
        DailyStockLevel(date=d["_id"], avg_stock_level=round(float(d["avg_stock_level"]), 1))
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
            prev_totals_docs = await col.aggregate([
                {"$match": prev_match},
                {"$group": {
                    "_id": None,
                    "total_stock_units": {"$sum": "$stock_level"},
                    "skus": {"$addToSet": "$sku"},
                }},
                {"$project": {
                    "total_stock_units": 1,
                    "total_skus": {"$size": "$skus"},
                }},
            ]).to_list(length=1)
            pt = prev_totals_docs[0] if prev_totals_docs else {}
            prev_stock = int(pt.get("total_stock_units", 0))
            prev_skus = int(pt.get("total_skus", 0))

            prev_below = await col.aggregate([
                {"$match": {**prev_match, "$expr": {"$lt": ["$stock_level", "$reorder_point"]}}},
                {"$group": {"_id": "$sku"}},
                {"$count": "total"},
            ]).to_list(length=1)
            prev_below_reorder = int(prev_below[0]["total"]) if prev_below else 0

            deltas = {}
            for field, cur, prv in [
                ("total_stock_units", float(total_stock_units), float(prev_stock)),
                ("total_skus", float(total_skus), float(prev_skus)),
                ("skus_below_reorder", float(skus_below_reorder), float(prev_below_reorder)),
            ]:
                d = pct_delta(cur, prv)
                if d is not None:
                    deltas[field] = d

    result = OperationsKpisOut(
        total_skus=total_skus,
        total_stock_units=total_stock_units,
        skus_below_reorder=skus_below_reorder,
        active_warehouses=active_warehouses,
        stock_by_warehouse=stock_by_warehouse,
        low_stock_skus=low_stock_skus,
        daily_stock_level=daily_stock_level,
        deltas=deltas,
    )
    await set_json(_key, result.model_dump(), ANALYTICS_TTL)
    return result
