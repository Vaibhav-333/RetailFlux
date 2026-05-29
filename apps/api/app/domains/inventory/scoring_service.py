"""Inventory health scoring: composite 0-100 score per SKU."""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Optional

from app.core.cache import ANALYTICS_TTL, get_json, inventory_key, set_json
from app.core.mongodb import get_mongo_db
from app.domains.inventory.aging_service import compute_doh
from app.schemas.inventory import HealthScoreOut, SkuHealthScore


# ── Pure scoring function (testable without DB) ───────────────────────────────


def compute_sku_health_score(
    doh: Optional[float],
    abc_class: Optional[str],
    xyz_class: Optional[str],
    sell_through: float,
    stock: float,
    reorder_point: float,
    has_cost_data: bool = True,
    target_doh_min: float = 14.0,
    target_doh_max: float = 90.0,
) -> tuple[float, dict[str, float]]:
    """Return (composite_score 0–100, component_scores dict).

    Component weights:
        velocity_balance  25%  — DOH within target band
        abc_class         20%  — revenue tier (A=1.0, B=0.6, C=0.2)
        xyz_class         15%  — demand predictability (X=1.0, Y=0.65, Z=0.3)
        supplier_est      15%  — estimated (0.80 default, no real supplier data yet)
        age_score         10%  — younger inventory (low DOH) scores higher
        sell_through      10%  — how well stock is converting to sales
        data_complete      5%  — penalise missing cost / class data
    """
    # 1. Velocity balance — DOH within target band
    if doh is None:
        vel_score = 0.0
    elif stock <= 0:
        vel_score = 0.0
    elif doh < 7:
        vel_score = 0.15  # Stockout risk
    elif doh < target_doh_min:
        vel_score = 0.55
    elif doh <= target_doh_max:
        vel_score = 1.0  # Sweet spot
    elif doh <= 180:
        vel_score = 0.4
    else:
        vel_score = 0.05  # Dead stock territory

    # 2. ABC class
    abc_scores = {"A": 1.0, "B": 0.6, "C": 0.2}
    abc_score = abc_scores.get(abc_class or "", 0.5)  # Unknown = neutral

    # 3. XYZ class
    xyz_scores = {"X": 1.0, "Y": 0.65, "Z": 0.3}
    xyz_score = xyz_scores.get(xyz_class or "", 0.5)

    # 4. Supplier reliability estimate (no real OTD data in staging yet)
    supplier_score = 0.80

    # 5. Age score — reward slow accumulation, penalise stagnation
    if doh is None:
        age_score = 0.0
    elif doh <= 30:
        age_score = 1.0
    elif doh <= 60:
        age_score = 0.75
    elif doh <= 90:
        age_score = 0.5
    elif doh <= 180:
        age_score = 0.25
    else:
        age_score = 0.0

    # 6. Sell-through (0..1)
    st_score = min(sell_through, 1.0)

    # 7. Data completeness
    data_score = 1.0 if has_cost_data else 0.0

    # Weighted sum
    weights = {
        "velocity_balance": 0.25,
        "abc_class": 0.20,
        "xyz_class": 0.15,
        "supplier_estimate": 0.15,
        "age": 0.10,
        "sell_through": 0.10,
        "data_completeness": 0.05,
    }
    component_values = {
        "velocity_balance": vel_score,
        "abc_class": abc_score,
        "xyz_class": xyz_score,
        "supplier_estimate": supplier_score,
        "age": age_score,
        "sell_through": st_score,
        "data_completeness": data_score,
    }
    composite = sum(weights[k] * component_values[k] for k in weights)
    composite_pct = round(composite * 100, 1)

    # Also include reorder-point penalty
    if stock < reorder_point and reorder_point > 0:
        composite_pct = max(0.0, composite_pct - 15.0)

    return composite_pct, {k: round(v * 100, 1) for k, v in component_values.items()}


# ── Async service ─────────────────────────────────────────────────────────────


async def get_health_scores(company_id: str) -> HealthScoreOut:
    """Return score distribution + top 20 + bottom 20 SKUs."""
    cache_key = inventory_key("health-scores", company_id)
    hit = await get_json(cache_key)
    if hit:
        return HealthScoreOut(**hit)

    db = get_mongo_db()
    col_ops = db["staging_operations"]
    col_sales = db["staging_sales"]
    col_proc = db["staging_procurement"]

    latest_docs = await col_ops.aggregate([
        {"$match": {"_company_id": company_id}},
        {"$group": {"_id": None, "max_date": {"$max": "$date"}}},
    ]).to_list(length=1)

    if not latest_docs:
        empty_dist = {b: 0 for b in ["0-20", "20-40", "40-60", "60-80", "80-100"]}
        return HealthScoreOut(avg_score=0.0, top_skus=[], bottom_skus=[], distribution=empty_dist, total_skus=0)

    latest_date = latest_docs[0]["max_date"]
    date_28d = (date.today() - timedelta(days=28)).isoformat()

    from app.domains.inventory.abc_xyz_service import get_abc_matrix, get_xyz_matrix

    stock_docs, demand_docs, cost_docs, abc_data, xyz_data = await asyncio.gather(
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
            {"$group": {"_id": "$sku", "total_qty": {"$sum": "$quantity"}, "revenue": {"$sum": "$revenue"}}},
        ]).to_list(length=5000),
        col_proc.aggregate([
            {"$match": {"_company_id": company_id}},
            {"$group": {"_id": "$sku", "avg_cost": {"$avg": "$unit_cost"}}},
        ]).to_list(length=5000),
        get_abc_matrix(company_id),
        get_xyz_matrix(company_id),
    )

    # Build ABC/XYZ maps
    abc_map: dict[str, str] = {}
    for cls, skus in abc_data.segments.items():
        for sku in skus:
            abc_map[sku] = cls
    xyz_map: dict[str, str] = {}
    for cls, skus in xyz_data.segments.items():
        for sku in skus:
            xyz_map[sku] = cls

    demand = {d["_id"]: float(d.get("total_qty", 0)) for d in demand_docs if d.get("_id")}
    revenue = {d["_id"]: float(d.get("revenue", 0)) for d in demand_docs if d.get("_id")}
    costs = {d["_id"]: float(d.get("avg_cost", 0)) for d in cost_docs if d.get("_id")}

    scored: list[SkuHealthScore] = []

    for doc in stock_docs:
        sku = doc.get("_id")
        if not sku:
            continue
        stock = float(doc.get("total_stock", 0))
        reorder_pt = float(doc.get("reorder_point", 0))
        unit_cost = costs.get(sku, 0.0)
        qty_28 = demand.get(sku, 0.0)
        rev_28 = revenue.get(sku, 0.0)
        avg_daily = qty_28 / 28 if qty_28 > 0 else 0.0
        doh = compute_doh(stock, avg_daily)
        opening = qty_28 + stock
        sell_through = qty_28 / opening if opening > 0 else 0.0

        score, components = compute_sku_health_score(
            doh=doh,
            abc_class=abc_map.get(sku),
            xyz_class=xyz_map.get(sku),
            sell_through=sell_through,
            stock=stock,
            reorder_point=reorder_pt,
            has_cost_data=unit_cost > 0,
        )
        scored.append(SkuHealthScore(
            sku=sku,
            score=score,
            components=components,
            category=None,  # Would need sku_master enrichment
            abc_class=abc_map.get(sku),
            xyz_class=xyz_map.get(sku),
        ))

    if not scored:
        empty_dist = {b: 0 for b in ["0-20", "20-40", "40-60", "60-80", "80-100"]}
        return HealthScoreOut(avg_score=0.0, top_skus=[], bottom_skus=[], distribution=empty_dist, total_skus=0)

    scored.sort(key=lambda x: x.score, reverse=True)
    avg_score = round(sum(s.score for s in scored) / len(scored), 1)

    # Score distribution
    distribution: dict[str, int] = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
    for s in scored:
        if s.score < 20:
            distribution["0-20"] += 1
        elif s.score < 40:
            distribution["20-40"] += 1
        elif s.score < 60:
            distribution["40-60"] += 1
        elif s.score < 80:
            distribution["60-80"] += 1
        else:
            distribution["80-100"] += 1

    result = HealthScoreOut(
        avg_score=avg_score,
        top_skus=scored[:20],
        bottom_skus=scored[-20:][::-1],
        distribution=distribution,
        total_skus=len(scored),
    )
    await set_json(cache_key, result.model_dump(), ANALYTICS_TTL * 2)
    return result
