"""ABC/XYZ classification algorithms and service."""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Optional

from app.core.cache import ANALYTICS_TTL, inventory_key, get_json, set_json
from app.core.mongodb import get_mongo_db
from app.schemas.inventory import AbcMatrixOut, AbcXyzCell, AbcXyzMatrixOut, XyzMatrixOut


# ── Pure classification functions (testable without DB) ───────────────────────


def classify_abc(sku_revenues: list[tuple[str, float]]) -> dict[str, str]:
    """Classify SKUs A/B/C by revenue contribution (A=top 80%, B=next 15%, C=rest)."""
    total = sum(r for _, r in sku_revenues)
    if total <= 0:
        return {sku: "C" for sku, _ in sku_revenues}
    cumulative = 0.0
    result: dict[str, str] = {}
    for sku, rev in sku_revenues:
        cumulative += rev
        pct = cumulative / total
        if pct <= 0.80:
            result[sku] = "A"
        elif pct <= 0.95:
            result[sku] = "B"
        else:
            result[sku] = "C"
    return result


def classify_xyz(weekly_demand: dict[str, list[float]]) -> dict[str, str]:
    """Classify SKUs X/Y/Z by demand variability (CV: X<0.25, Y<0.50, Z≥0.50)."""
    result: dict[str, str] = {}
    for sku, demands in weekly_demand.items():
        if len(demands) < 2 or sum(demands) == 0:
            result[sku] = "Z"
            continue
        mean_d = sum(demands) / len(demands)
        if mean_d == 0:
            result[sku] = "Z"
            continue
        variance = sum((d - mean_d) ** 2 for d in demands) / len(demands)
        cv = math.sqrt(variance) / mean_d
        if cv < 0.25:
            result[sku] = "X"
        elif cv < 0.50:
            result[sku] = "Y"
        else:
            result[sku] = "Z"
    return result


# ── Async service functions ───────────────────────────────────────────────────


async def get_abc_matrix(company_id: str) -> AbcMatrixOut:
    cache_key = inventory_key("abc", company_id)
    hit = await get_json(cache_key)
    if hit:
        return AbcMatrixOut(**hit)

    col = get_mongo_db()["staging_sales"]
    sku_rev_docs = await col.aggregate([
        {"$match": {"_company_id": company_id}},
        {"$group": {"_id": "$sku", "revenue": {"$sum": "$revenue"}}},
        {"$sort": {"revenue": -1}},
    ]).to_list(length=5000)

    sku_revenues = [(d["_id"], float(d.get("revenue", 0))) for d in sku_rev_docs if d.get("_id")]
    classification = classify_abc(sku_revenues)

    total_rev = sum(r for _, r in sku_revenues)
    segments: dict[str, list[str]] = {"A": [], "B": [], "C": []}
    rev_by_cls: dict[str, float] = {"A": 0.0, "B": 0.0, "C": 0.0}

    for sku, rev in sku_revenues:
        cls = classification.get(sku, "C")
        segments[cls].append(sku)
        rev_by_cls[cls] = rev_by_cls.get(cls, 0.0) + rev

    revenue_pcts = {
        cls: round(rev_by_cls[cls] / total_rev * 100, 1) if total_rev > 0 else 0.0
        for cls in ("A", "B", "C")
    }
    result = AbcMatrixOut(
        segments=segments,
        sku_counts={cls: len(skus) for cls, skus in segments.items()},
        revenue_pcts=revenue_pcts,
        total_revenue=round(total_rev, 2),
    )
    await set_json(cache_key, result.model_dump(), ANALYTICS_TTL * 6)  # 30 min
    return result


async def get_xyz_matrix(company_id: str) -> XyzMatrixOut:
    cache_key = inventory_key("xyz", company_id)
    hit = await get_json(cache_key)
    if hit:
        return XyzMatrixOut(**hit)

    thirteen_weeks_ago = (date.today() - timedelta(weeks=13)).isoformat()
    col = get_mongo_db()["staging_sales"]
    weekly_docs = await col.aggregate([
        {"$match": {"_company_id": company_id, "date": {"$gte": thirteen_weeks_ago}}},
        {
            "$group": {
                "_id": {
                    "sku": "$sku",
                    "week": {"$dateToString": {"format": "%Y-W%V", "date": {"$toDate": "$date"}}},
                },
                "qty": {"$sum": "$quantity"},
            }
        },
    ]).to_list(length=50000)

    weekly_demand: dict[str, list[float]] = {}
    for d in weekly_docs:
        sku = d["_id"].get("sku")
        if not sku:
            continue
        weekly_demand.setdefault(sku, []).append(float(d.get("qty", 0)))

    classification = classify_xyz(weekly_demand)

    segments: dict[str, list[str]] = {"X": [], "Y": [], "Z": []}
    for sku, cls in classification.items():
        segments[cls].append(sku)

    result = XyzMatrixOut(
        segments=segments,
        sku_counts={cls: len(skus) for cls, skus in segments.items()},
        cv_ranges={"X": "CV < 0.25", "Y": "0.25 ≤ CV < 0.50", "Z": "CV ≥ 0.50"},
    )
    await set_json(cache_key, result.model_dump(), ANALYTICS_TTL * 6)
    return result


async def get_abc_xyz_matrix(company_id: str) -> AbcXyzMatrixOut:
    cache_key = inventory_key("abc-xyz", company_id)
    hit = await get_json(cache_key)
    if hit:
        return AbcXyzMatrixOut(**hit)

    import asyncio
    abc_result, xyz_result = await asyncio.gather(
        get_abc_matrix(company_id),
        get_xyz_matrix(company_id),
    )

    abc_map: dict[str, str] = {}
    for cls, skus in abc_result.segments.items():
        for sku in skus:
            abc_map[sku] = cls

    xyz_map: dict[str, str] = {}
    for cls, skus in xyz_result.segments.items():
        for sku in skus:
            xyz_map[sku] = cls

    rev_map: dict[str, float] = {}
    col = get_mongo_db()["staging_sales"]
    rev_docs = await col.aggregate([
        {"$match": {"_company_id": company_id}},
        {"$group": {"_id": "$sku", "revenue": {"$sum": "$revenue"}}},
    ]).to_list(length=5000)
    for d in rev_docs:
        if d.get("_id"):
            rev_map[d["_id"]] = float(d.get("revenue", 0))

    all_skus = set(abc_map) | set(xyz_map)
    cell_map: dict[tuple[str, str], AbcXyzCell] = {}
    for abc in ("A", "B", "C"):
        for xyz in ("X", "Y", "Z"):
            cell_map[(abc, xyz)] = AbcXyzCell(abc=abc, xyz=xyz, sku_count=0, total_revenue=0.0, skus=[])

    for sku in all_skus:
        abc = abc_map.get(sku, "C")
        xyz = xyz_map.get(sku, "Z")
        key = (abc, xyz)
        cell = cell_map[key]
        cell.sku_count += 1
        cell.total_revenue += rev_map.get(sku, 0.0)
        cell.skus.append(sku)

    cells = [c for c in cell_map.values()]
    total_rev = sum(c.total_revenue for c in cells)
    result = AbcXyzMatrixOut(
        cells=cells,
        total_skus=len(all_skus),
        total_revenue=round(total_rev, 2),
    )
    await set_json(cache_key, result.model_dump(), ANALYTICS_TTL * 6)
    return result
