"""Dynamic Pricing suggestions — generate and serve per-SKU price recommendations.

Stored in MongoDB ``pricing_suggestions`` collection.
Regenerated weekly via Celery (pricing_weekly.py).
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from app.core.cache import ANALYTICS_TTL, get_json, set_json
from app.core.mongodb import get_mongo_db
from app.domains.pricing.elasticity_service import (
    estimate_elasticity,
    optimal_price_range,
)

_CACHE_PREFIX = "rf:cache:pricing:suggestions"
SUGGESTIONS_COLLECTION = "pricing_suggestions"


def _cache_key(company_id: str, page: int, page_size: int) -> str:
    return f"{_CACHE_PREFIX}:{company_id}:{page}:{page_size}"


async def _build_suggestions(company_id: str) -> list[dict]:
    """Compute pricing suggestions for all SKUs with sufficient data."""
    db = get_mongo_db()
    col_sales = db["staging_sales"]
    col_proc = db["staging_procurement"]

    date_90d = (date.today() - timedelta(days=90)).isoformat()

    # Fetch daily (price, qty) per SKU and avg cost
    sales_docs, cost_docs = await asyncio.gather(
        col_sales.aggregate([
            {"$match": {"_company_id": company_id, "date": {"$gte": date_90d}}},
            {"$group": {
                "_id": {"sku": "$sku", "date": "$date"},
                "total_qty": {"$sum": "$quantity"},
                "avg_price": {"$avg": "$unit_price"},
            }},
            {"$sort": {"_id.date": 1}},
        ]).to_list(length=100000),
        col_proc.aggregate([
            {"$match": {"_company_id": company_id}},
            {"$group": {
                "_id": "$sku",
                "avg_cost": {"$avg": "$unit_cost"},
            }},
        ]).to_list(length=5000),
    )

    costs = {d["_id"]: float(d.get("avg_cost", 0)) for d in cost_docs if d.get("_id")}

    # Group by SKU
    sku_data: dict[str, dict] = {}
    for doc in sales_docs:
        key = doc.get("_id", {})
        sku = key.get("sku", "")
        if not sku:
            continue
        if sku not in sku_data:
            sku_data[sku] = {"prices": [], "quantities": [], "total_rev": 0.0, "total_qty": 0.0}
        sku_data[sku]["prices"].append(float(doc.get("avg_price", 0)))
        sku_data[sku]["quantities"].append(float(doc.get("total_qty", 0)))
        sku_data[sku]["total_rev"] += float(doc.get("avg_price", 0)) * float(doc.get("total_qty", 0))
        sku_data[sku]["total_qty"] += float(doc.get("total_qty", 0))

    suggestions = []
    now = datetime.now(timezone.utc)

    for sku, data in sku_data.items():
        unit_cost = costs.get(sku, 0.0)
        prices = data["prices"]
        qtys = data["quantities"]
        total_qty = data["total_qty"]

        if total_qty <= 0 or not prices:
            continue

        current_price = data["total_rev"] / max(1.0, total_qty)
        avg_daily_qty = total_qty / 90

        elas = estimate_elasticity(prices, qtys)
        if not elas["reliable"]:
            # Use default -1.2 elasticity for goods with insufficient data
            elas["elasticity"] = -1.2

        if unit_cost <= 0:
            continue  # No cost data → skip

        opt = optimal_price_range(
            current_price=current_price,
            unit_cost=unit_cost,
            elasticity=elas["elasticity"],
        )

        suggested_price = opt["optimal_price"]
        lift_pct = opt["expected_lift_pct"]

        if abs(suggested_price - current_price) / max(1.0, current_price) < 0.02:
            continue  # < 2% change — not worth surfacing

        current_margin_pct = (current_price - unit_cost) / max(1.0, current_price) * 100
        suggested_margin_pct = (suggested_price - unit_cost) / max(1.0, suggested_price) * 100

        direction = "increase" if suggested_price > current_price else "decrease"
        reason = (
            "Demand is relatively inelastic — raising price improves margin without significant volume loss."
            if direction == "increase"
            else "Strong demand elasticity detected — a modest price reduction is expected to lift volume and total GP."
        )

        confidence = "high" if elas["reliable"] and elas["r_squared"] > 0.2 else "medium"
        if not elas["reliable"]:
            confidence = "low"

        suggestions.append({
            "sku": sku,
            "current_price": round(current_price, 2),
            "suggested_price": round(suggested_price, 2),
            "unit_cost": round(unit_cost, 2),
            "current_margin_pct": round(current_margin_pct, 1),
            "suggested_margin_pct": round(suggested_margin_pct, 1),
            "expected_lift_pct": round(lift_pct, 2),
            "direction": direction,
            "reason": reason,
            "confidence": confidence,
            "elasticity": round(elas["elasticity"], 3),
            "r_squared": round(elas["r_squared"], 3),
            "avg_daily_qty": round(avg_daily_qty, 2),
            "_company_id": company_id,
            "generated_at": now,
        })

    suggestions.sort(key=lambda x: abs(x["expected_lift_pct"]), reverse=True)
    return suggestions


async def refresh_pricing_suggestions(company_id: str) -> int:
    """Recompute all suggestions and upsert into MongoDB. Returns count."""
    db = get_mongo_db()
    col = db[SUGGESTIONS_COLLECTION]

    suggestions = await _build_suggestions(company_id)
    if not suggestions:
        return 0

    # Delete old suggestions for this company
    await col.delete_many({"_company_id": company_id})
    await col.insert_many(suggestions)
    return len(suggestions)


async def get_pricing_suggestions(
    company_id: str,
    page: int = 1,
    page_size: int = 20,
    direction: Optional[str] = None,
    min_lift: Optional[float] = None,
) -> dict:
    """Return paginated pricing suggestions from cache/Mongo."""
    cache_key = _cache_key(company_id, page, page_size)
    hit = await get_json(cache_key)
    if hit:
        return hit

    db = get_mongo_db()
    col = db[SUGGESTIONS_COLLECTION]

    query: dict = {"_company_id": company_id}
    if direction:
        query["direction"] = direction
    if min_lift is not None:
        query["expected_lift_pct"] = {"$gte": min_lift}

    total = await col.count_documents(query)
    skip = (page - 1) * page_size
    docs = await col.find(
        query,
        {"_id": 0, "_company_id": 0},
    ).sort("expected_lift_pct", -1).skip(skip).limit(page_size).to_list(length=page_size)

    # If no cached suggestions, compute on-the-fly
    if total == 0:
        all_suggestions = await _build_suggestions(company_id)
        for s in all_suggestions:
            s.pop("_company_id", None)
            if "generated_at" in s:
                s["generated_at"] = s["generated_at"].isoformat()
        total = len(all_suggestions)
        docs = all_suggestions[skip: skip + page_size]
    else:
        for doc in docs:
            if "generated_at" in doc and hasattr(doc["generated_at"], "isoformat"):
                doc["generated_at"] = doc["generated_at"].isoformat()

    result = {
        "items": docs,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    await set_json(cache_key, result, ANALYTICS_TTL)
    return result


async def get_pricing_summary(company_id: str) -> dict:
    """Return high-level summary of pricing opportunity."""
    cache_key = f"rf:cache:pricing:summary:{company_id}"
    hit = await get_json(cache_key)
    if hit:
        return hit

    db = get_mongo_db()
    col = db[SUGGESTIONS_COLLECTION]

    docs = await col.find(
        {"_company_id": company_id},
        {"expected_lift_pct": 1, "direction": 1, "confidence": 1},
    ).to_list(length=10000)

    if not docs:
        # Trigger on-the-fly build
        suggestions = await _build_suggestions(company_id)
        docs = [{"expected_lift_pct": s["expected_lift_pct"], "direction": s["direction"], "confidence": s["confidence"]}
                for s in suggestions]

    total = len(docs)
    increase_count = sum(1 for d in docs if d.get("direction") == "increase")
    decrease_count = sum(1 for d in docs if d.get("direction") == "decrease")
    avg_lift = sum(d.get("expected_lift_pct", 0) for d in docs) / max(1, total)
    high_conf = sum(1 for d in docs if d.get("confidence") == "high")

    result = {
        "total_skus": total,
        "increase_count": increase_count,
        "decrease_count": decrease_count,
        "avg_expected_lift_pct": round(avg_lift, 2),
        "high_confidence_count": high_conf,
    }
    await set_json(cache_key, result, ANALYTICS_TTL)
    return result
