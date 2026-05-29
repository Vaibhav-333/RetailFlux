"""Profit levers — ranked actions most likely to improve gross profit.

Levers are derived by computing delta-GP from:
  1. Reducing COGS (supplier cost negotiation)
  2. Recovering lost revenue on high-demand / out-of-stock SKUs
  3. Reducing markdown intensity on slow-movers (holding price)
  4. Shifting mix toward high-margin categories
  5. Reducing dead-stock write-off exposure
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta

from app.core.cache import ANALYTICS_TTL, get_json, set_json
from app.core.mongodb import get_mongo_db

_CACHE_PREFIX = "rf:cache:profit:levers"


def _cache_key(company_id: str) -> str:
    return f"{_CACHE_PREFIX}:{company_id}"


async def get_profit_levers(company_id: str) -> dict:
    """Return top-10 ranked levers with simulated GP lift."""
    cache_key = _cache_key(company_id)
    hit = await get_json(cache_key)
    if hit:
        return hit

    db = get_mongo_db()
    col_sales = db["staging_sales"]
    col_proc = db["staging_procurement"]
    col_ops = db["staging_operations"]

    date_28d = (date.today() - timedelta(days=28)).isoformat()

    sales_docs, cost_docs, stock_docs = await asyncio.gather(
        col_sales.aggregate([
            {"$match": {"_company_id": company_id, "date": {"$gte": date_28d}}},
            {"$group": {
                "_id": {"sku": "$sku", "category": "$category"},
                "total_qty": {"$sum": "$quantity"},
                "total_revenue": {"$sum": "$revenue"},
                "avg_price": {"$avg": "$unit_price"},
            }},
        ]).to_list(length=5000),
        col_proc.aggregate([
            {"$match": {"_company_id": company_id, "date": {"$gte": date_28d}}},
            {"$group": {
                "_id": "$sku",
                "avg_cost": {"$avg": "$unit_cost"},
                "total_cogs": {"$sum": {"$multiply": ["$unit_cost", "$quantity"]}},
            }},
        ]).to_list(length=5000),
        col_ops.aggregate([
            {"$match": {"_company_id": company_id}},
            {"$group": {"_id": None, "max_date": {"$max": "$date"}}},
        ]).to_list(length=1),
    )

    latest_date = stock_docs[0]["max_date"] if stock_docs else None
    costs = {d["_id"]: float(d.get("avg_cost", 0)) for d in cost_docs if d.get("_id")}
    cogs_total = {d["_id"]: float(d.get("total_cogs", 0)) for d in cost_docs if d.get("_id")}

    total_revenue = 0.0
    total_cogs = 0.0
    category_stats: dict[str, dict] = {}

    for doc in sales_docs:
        key = doc.get("_id", {})
        sku = key.get("sku", "")
        cat = key.get("category", "General") or "General"
        qty = float(doc.get("total_qty", 0))
        rev = float(doc.get("total_revenue", 0))
        avg_price = float(doc.get("avg_price", 0))
        cogs = cogs_total.get(sku, 0.0)
        unit_cost = costs.get(sku, 0.0)
        gp = rev - cogs

        total_revenue += rev
        total_cogs += cogs

        if cat not in category_stats:
            category_stats[cat] = {"revenue": 0, "cogs": 0, "qty": 0, "skus": []}
        category_stats[cat]["revenue"] += rev
        category_stats[cat]["cogs"] += cogs
        category_stats[cat]["qty"] += qty
        category_stats[cat]["skus"].append({
            "sku": sku, "rev": rev, "cogs": cogs, "gp": gp,
            "avg_price": avg_price, "unit_cost": unit_cost, "qty": qty,
        })

    total_gp = total_revenue - total_cogs

    levers: list[dict] = []

    # ── Lever 1: 5% COGS reduction on top-spend SKUs ─────────────────────────
    top_cogs_skus = sorted(
        [(sku, v) for sku, v in cogs_total.items()],
        key=lambda x: x[1], reverse=True,
    )[:10]
    cogs_5pct_lift = sum(v * 0.05 for _, v in top_cogs_skus)
    if cogs_5pct_lift > 0:
        levers.append({
            "id": "reduce-cogs-5pct",
            "title": "Negotiate 5% COGS reduction on top-10 cost SKUs",
            "description": "A 5% unit-cost reduction on your highest-cost SKUs adds directly to gross profit.",
            "category": "Cost",
            "estimated_gp_lift": round(cogs_5pct_lift, 2),
            "effort": "medium",
            "confidence": "high",
            "action": "create_task",
            "skus": [s for s, _ in top_cogs_skus[:5]],
        })

    # ── Lever 2: Recover 10% of lost revenue on stockout SKUs ────────────────
    if latest_date:
        stockout_docs = await col_ops.aggregate([
            {"$match": {"_company_id": company_id, "date": latest_date, "stock_level": 0}},
            {"$group": {"_id": "$sku"}},
        ]).to_list(length=1000)

        stockout_skus = {d["_id"] for d in stockout_docs if d.get("_id")}
        stockout_revenue = sum(
            float(doc.get("total_revenue", 0))
            for doc in sales_docs
            if doc.get("_id", {}).get("sku", "") in stockout_skus
        ) * (28 / 7)  # Annualise weekly rate

        recovery_10pct = stockout_revenue * 0.10
        if stockout_skus and recovery_10pct > 0:
            avg_margin = total_gp / max(1.0, total_revenue)
            levers.append({
                "id": "recover-stockout-revenue",
                "title": f"Recover 10% lost revenue on {len(stockout_skus)} stockout SKUs",
                "description": "Currently out-of-stock SKUs represent missed revenue. Replenishing reduces lost sales.",
                "category": "Volume",
                "estimated_gp_lift": round(recovery_10pct * avg_margin, 2),
                "effort": "low",
                "confidence": "medium",
                "action": "view_reorder_queue",
                "skus": list(stockout_skus)[:5],
            })

    # ── Lever 3: Reduce markdown on top-10 slow movers ───────────────────────
    slow_movers = []
    for doc in sales_docs:
        sku = doc.get("_id", {}).get("sku", "")
        qty = float(doc.get("total_qty", 0))
        rev = float(doc.get("total_revenue", 0))
        avg_price = float(doc.get("avg_price", 0))
        unit_cost = costs.get(sku, 0.0)
        margin = (avg_price - unit_cost) / max(1.0, avg_price)
        if qty < 5 and rev > 0 and margin < 0.15:
            slow_movers.append({"sku": sku, "rev": rev, "margin": margin})

    slow_movers.sort(key=lambda x: x["rev"], reverse=True)
    markdown_recovery = sum(
        s["rev"] * 0.08  # Assume 8% lift from holding price 1 week longer
        for s in slow_movers[:10]
    )
    if markdown_recovery > 0:
        levers.append({
            "id": "reduce-markdown-slow-movers",
            "title": "Hold price on 10 low-margin slow movers for 1 additional week",
            "description": "Premature markdown erodes margin. Delaying by 1 week recovers ~8% of revenue per unit.",
            "category": "Price",
            "estimated_gp_lift": round(markdown_recovery, 2),
            "effort": "low",
            "confidence": "medium",
            "action": "view_pricing_suggestions",
            "skus": [s["sku"] for s in slow_movers[:5]],
        })

    # ── Lever 4: Shift mix toward high-margin categories ─────────────────────
    cat_margins = {
        cat: (stats["revenue"] - stats["cogs"]) / max(1.0, stats["revenue"])
        for cat, stats in category_stats.items()
    }
    if len(cat_margins) >= 2:
        best_cat = max(cat_margins, key=lambda c: cat_margins[c])
        worst_cat = min(cat_margins, key=lambda c: cat_margins[c])
        best_margin = cat_margins[best_cat]
        worst_margin = cat_margins[worst_cat]
        worst_rev = category_stats[worst_cat]["revenue"]
        if best_margin - worst_margin > 0.1 and worst_rev > 0:
            mix_lift = worst_rev * 0.05 * (best_margin - worst_margin)
            levers.append({
                "id": "shift-mix-high-margin",
                "title": f"Shift 5% revenue from {worst_cat} → {best_cat} (higher margin)",
                "description": f"{best_cat} margin is {best_margin:.0%} vs {worst_margin:.0%} for {worst_cat}.",
                "category": "Mix",
                "estimated_gp_lift": round(mix_lift, 2),
                "effort": "high",
                "confidence": "medium",
                "action": "view_profit_intelligence",
                "skus": [],
            })

    # ── Lever 5: Clear dead stock before further aging ───────────────────────
    dead_cogs_exposure = sum(
        float(d.get("total_cogs", 0))
        for d in cost_docs
        if d.get("_id", "") not in {
            doc.get("_id", {}).get("sku", "") for doc in sales_docs
        }
    )
    if dead_cogs_exposure > 0:
        write_off_risk = dead_cogs_exposure * 0.15
        levers.append({
            "id": "clear-dead-stock",
            "title": "Liquidate dead-stock inventory to avoid write-off",
            "description": f"SKUs with no sales in 28+ days represent ${dead_cogs_exposure:,.0f} in tied capital.",
            "category": "Cost",
            "estimated_gp_lift": round(write_off_risk, 2),
            "effort": "medium",
            "confidence": "low",
            "action": "view_dead_stock",
            "skus": [],
        })

    # Sort by estimated GP lift descending, take top 10
    levers.sort(key=lambda x: x["estimated_gp_lift"], reverse=True)
    levers = levers[:10]

    result = {
        "generated_at": date.today().isoformat(),
        "baseline_gp_28d": round(total_gp, 2),
        "total_potential_lift": round(sum(l["estimated_gp_lift"] for l in levers), 2),
        "levers": levers,
    }

    await set_json(cache_key, result, ANALYTICS_TTL)
    return result
