from datetime import date, timedelta
from typing import Optional

from app.core.cache import ANALYTICS_TTL, analytics_key, get_json, set_json
from app.core.mongodb import get_mongo_db
from app.domains.analytics.utils import compute_compare_period, parse_dims, pct_delta
from app.schemas.analytics import (
    DailySpend,
    ProcurementKpisOut,
    SkuCost,
    SupplierSpend,
)


async def get_procurement_kpis(
    company_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    compare_to: Optional[str] = None,
    dims: Optional[str] = None,
) -> ProcurementKpisOut:
    if not date_from:
        date_from = (date.today() - timedelta(days=90)).isoformat()
    if not date_to:
        date_to = date.today().isoformat()

    _key = analytics_key("procurement", company_id, date_from, date_to)
    if compare_to or dims:
        _key += f":{compare_to or ''}:{dims or ''}"

    _hit = await get_json(_key)
    if _hit:
        return ProcurementKpisOut(**_hit)

    col = get_mongo_db()["staging_procurement"]

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
            "total_spend": {"$sum": {"$multiply": ["$quantity", "$unit_cost"]}},
            "total_units": {"$sum": "$quantity"},
            "unique_suppliers": {"$addToSet": "$supplier_id"},
            "avg_lead_days": {"$avg": "$lead_days"},
        }},
        {"$addFields": {"unique_suppliers": {"$size": "$unique_suppliers"}}},
    ]).to_list(length=1)

    totals = totals_docs[0] if totals_docs else {}
    total_spend: float = round(float(totals.get("total_spend", 0.0)), 2)
    total_units: int = int(totals.get("total_units", 0))
    unique_suppliers: int = int(totals.get("unique_suppliers", 0))
    avg_lead_days: float = round(float(totals.get("avg_lead_days", 0.0)), 1)

    # ── Top 10 suppliers by spend ─────────────────────────────────────────────
    supplier_docs = await col.aggregate([
        {"$match": match},
        {"$group": {
            "_id": "$supplier_id",
            "spend": {"$sum": {"$multiply": ["$quantity", "$unit_cost"]}},
        }},
        {"$sort": {"spend": -1}},
    ]).to_list(length=10)
    top_suppliers = [
        SupplierSpend(
            supplier_id=d["_id"] or "Unknown",
            spend=round(float(d["spend"]), 2),
        )
        for d in supplier_docs
    ]

    # ── Daily spend time-series ───────────────────────────────────────────────
    daily_docs = await col.aggregate([
        {"$match": match},
        {"$group": {
            "_id": "$date",
            "spend": {"$sum": {"$multiply": ["$quantity", "$unit_cost"]}},
        }},
        {"$sort": {"_id": 1}},
    ]).to_list(length=365)
    daily_spend = [
        DailySpend(date=d["_id"], spend=round(float(d["spend"]), 2))
        for d in daily_docs
    ]

    # ── Top 10 SKUs by avg unit cost ──────────────────────────────────────────
    sku_docs = await col.aggregate([
        {"$match": match},
        {"$group": {
            "_id": "$sku",
            "avg_unit_cost": {"$avg": "$unit_cost"},
        }},
        {"$sort": {"avg_unit_cost": -1}},
    ]).to_list(length=10)
    top_sku_costs = [
        SkuCost(sku=d["_id"] or "Unknown", avg_unit_cost=round(float(d["avg_unit_cost"]), 2))
        for d in sku_docs
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
                    "total_spend": {"$sum": {"$multiply": ["$quantity", "$unit_cost"]}},
                    "total_units": {"$sum": "$quantity"},
                    "unique_suppliers": {"$addToSet": "$supplier_id"},
                    "avg_lead_days": {"$avg": "$lead_days"},
                }},
                {"$addFields": {"unique_suppliers": {"$size": "$unique_suppliers"}}},
            ]).to_list(length=1)
            prev = prev_docs[0] if prev_docs else {}
            prev_spend = round(float(prev.get("total_spend", 0.0)), 2)
            prev_units = int(prev.get("total_units", 0))
            prev_lead = round(float(prev.get("avg_lead_days", 0.0)), 1)
            deltas = {}
            for field, cur, prv in [
                ("total_spend", total_spend, prev_spend),
                ("total_units", float(total_units), float(prev_units)),
                ("avg_lead_days", avg_lead_days, prev_lead),
            ]:
                d = pct_delta(cur, prv)
                if d is not None:
                    deltas[field] = d

    result = ProcurementKpisOut(
        total_spend=total_spend,
        total_units=total_units,
        unique_suppliers=unique_suppliers,
        avg_lead_days=avg_lead_days,
        top_suppliers=top_suppliers,
        daily_spend=daily_spend,
        top_sku_costs=top_sku_costs,
        deltas=deltas,
    )
    await set_json(_key, result.model_dump(), ANALYTICS_TTL)
    return result
