"""Profit attribution waterfall — decomposes gross-profit delta into:
   Volume · Price · Mix · Cost · Promo drivers.

Formula (contribution analysis):
  ΔGP = (Δvolume × baseline_price) + (Δprice × baseline_volume)
        + (Δmix × baseline_GP_per_unit) + (Δcost × −1 × baseline_volume)
        + promo_effect (residual)
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta

from app.core.cache import ANALYTICS_TTL, get_json, set_json
from app.core.mongodb import get_mongo_db

_CACHE_PREFIX = "rf:cache:profit:attribution"


def _cache_key(company_id: str, period: str, compare_period: str) -> str:
    return f"{_CACHE_PREFIX}:{company_id}:{period}:{compare_period}"


def _date_range(period_label: str) -> tuple[str, str]:
    """Convert label → (from, to) ISO date strings."""
    today = date.today()
    if period_label == "7d":
        return (today - timedelta(days=7)).isoformat(), today.isoformat()
    if period_label == "28d":
        return (today - timedelta(days=28)).isoformat(), today.isoformat()
    if period_label == "90d":
        return (today - timedelta(days=90)).isoformat(), today.isoformat()
    # Default: last 30 days
    return (today - timedelta(days=30)).isoformat(), today.isoformat()


async def _period_stats(
    company_id: str,
    date_from: str,
    date_to: str,
) -> dict:
    """Aggregate period stats per SKU/category."""
    db = get_mongo_db()
    col_sales = db["staging_sales"]
    col_proc = db["staging_procurement"]

    sales_docs, cost_docs = await asyncio.gather(
        col_sales.aggregate([
            {"$match": {
                "_company_id": company_id,
                "date": {"$gte": date_from, "$lte": date_to},
            }},
            {"$group": {
                "_id": {"sku": "$sku", "category": "$category"},
                "total_qty": {"$sum": "$quantity"},
                "total_revenue": {"$sum": "$revenue"},
                "avg_price": {"$avg": "$unit_price"},
            }},
        ]).to_list(length=5000),
        col_proc.aggregate([
            {"$match": {
                "_company_id": company_id,
                "date": {"$gte": date_from, "$lte": date_to},
            }},
            {"$group": {
                "_id": "$sku",
                "avg_cost": {"$avg": "$unit_cost"},
                "total_cogs": {"$sum": {"$multiply": ["$unit_cost", "$quantity"]}},
            }},
        ]).to_list(length=5000),
    )

    costs = {d["_id"]: {"avg_cost": float(d.get("avg_cost", 0)), "total_cogs": float(d.get("total_cogs", 0))}
             for d in cost_docs if d.get("_id")}

    total_qty = 0.0
    total_revenue = 0.0
    total_cogs = 0.0
    category_revenue: dict[str, float] = {}

    for doc in sales_docs:
        key = doc.get("_id", {})
        sku = key.get("sku", "")
        cat = key.get("category", "General") or "General"
        qty = float(doc.get("total_qty", 0))
        rev = float(doc.get("total_revenue", 0))
        cogs = costs.get(sku, {}).get("total_cogs", 0.0)

        total_qty += qty
        total_revenue += rev
        total_cogs += cogs
        category_revenue[cat] = category_revenue.get(cat, 0.0) + rev

    total_gp = total_revenue - total_cogs
    avg_price = total_revenue / max(1.0, total_qty)
    avg_cost = total_cogs / max(1.0, total_qty)

    return {
        "total_qty": total_qty,
        "total_revenue": total_revenue,
        "total_cogs": total_cogs,
        "total_gp": total_gp,
        "avg_price": avg_price,
        "avg_cost": avg_cost,
        "category_revenue": category_revenue,
    }


async def get_profit_attribution(
    company_id: str,
    current_period: str = "28d",
    compare_period: str = "prev_28d",
) -> dict:
    """Return waterfall decomposition of GP delta between two periods."""
    cache_key = _cache_key(company_id, current_period, compare_period)
    hit = await get_json(cache_key)
    if hit:
        return hit

    today = date.today()

    if current_period == "28d":
        cur_from = (today - timedelta(days=28)).isoformat()
        cur_to = today.isoformat()
        prev_from = (today - timedelta(days=56)).isoformat()
        prev_to = (today - timedelta(days=29)).isoformat()
    elif current_period == "7d":
        cur_from = (today - timedelta(days=7)).isoformat()
        cur_to = today.isoformat()
        prev_from = (today - timedelta(days=14)).isoformat()
        prev_to = (today - timedelta(days=8)).isoformat()
    else:  # 90d
        cur_from = (today - timedelta(days=90)).isoformat()
        cur_to = today.isoformat()
        prev_from = (today - timedelta(days=180)).isoformat()
        prev_to = (today - timedelta(days=91)).isoformat()

    current, previous = await asyncio.gather(
        _period_stats(company_id, cur_from, cur_to),
        _period_stats(company_id, prev_from, prev_to),
    )

    # Waterfall attribution
    dv = current["total_qty"] - previous["total_qty"]
    dp = current["avg_price"] - previous["avg_price"]
    dc = current["avg_cost"] - previous["avg_cost"]

    baseline_price = previous["avg_price"]
    baseline_vol = previous["total_qty"]
    baseline_gp_pu = previous["avg_price"] - previous["avg_cost"]

    volume_effect = round(dv * baseline_gp_pu, 2)
    price_effect = round(dp * baseline_vol, 2)
    cost_effect = round(-dc * current["total_qty"], 2)

    # Mix effect: change in category revenue mix vs baseline margin
    cur_cats = current["category_revenue"]
    prev_cats = previous["category_revenue"]
    prev_total = max(1.0, previous["total_revenue"])
    cur_total = max(1.0, current["total_revenue"])
    mix_effect = 0.0
    for cat, cur_rev in cur_cats.items():
        prev_rev = prev_cats.get(cat, 0.0)
        cur_share = cur_rev / cur_total
        prev_share = prev_rev / prev_total
        # Assume ~40% gross margin per category (placeholder — enrich with real data)
        est_margin = 0.40
        mix_effect += (cur_share - prev_share) * cur_total * est_margin
    mix_effect = round(mix_effect, 2)

    # Promo / residual: what's left unexplained
    total_delta = round(current["total_gp"] - previous["total_gp"], 2)
    explained = volume_effect + price_effect + cost_effect + mix_effect
    promo_residual = round(total_delta - explained, 2)

    waterfall = [
        {"label": "Prior Period GP", "value": round(previous["total_gp"], 2), "type": "base"},
        {"label": "Volume", "value": volume_effect, "type": "delta"},
        {"label": "Price", "value": price_effect, "type": "delta"},
        {"label": "Mix", "value": mix_effect, "type": "delta"},
        {"label": "Cost", "value": cost_effect, "type": "delta"},
        {"label": "Promo / Other", "value": promo_residual, "type": "delta"},
        {"label": "Current Period GP", "value": round(current["total_gp"], 2), "type": "total"},
    ]

    result = {
        "period": current_period,
        "compare_period": compare_period,
        "current": {
            "total_gp": round(current["total_gp"], 2),
            "total_revenue": round(current["total_revenue"], 2),
            "total_cogs": round(current["total_cogs"], 2),
        },
        "previous": {
            "total_gp": round(previous["total_gp"], 2),
            "total_revenue": round(previous["total_revenue"], 2),
            "total_cogs": round(previous["total_cogs"], 2),
        },
        "total_delta": total_delta,
        "waterfall": waterfall,
    }

    await set_json(cache_key, result, ANALYTICS_TTL)
    return result
