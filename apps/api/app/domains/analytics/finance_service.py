from datetime import date, timedelta
from typing import Optional

from app.core.cache import ANALYTICS_TTL, analytics_key, get_json, set_json
from app.core.mongodb import get_mongo_db
from app.domains.analytics.utils import compute_compare_period, parse_dims, pct_delta
from app.schemas.analytics import (
    CategoryRevenue,
    DailyGrossProfit,
    FinanceKpisOut,
    MonthlyPnL,
)


async def get_finance_kpis(
    company_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    compare_to: Optional[str] = None,
    dims: Optional[str] = None,
) -> FinanceKpisOut:
    if not date_from:
        date_from = (date.today() - timedelta(days=90)).isoformat()
    if not date_to:
        date_to = date.today().isoformat()

    _key = analytics_key("finance", company_id, date_from, date_to)
    if compare_to or dims:
        _key += f":{compare_to or ''}:{dims or ''}"

    _hit = await get_json(_key)
    if _hit:
        return FinanceKpisOut(**_hit)

    col = get_mongo_db()["staging_finance"]

    dim_filter = parse_dims(dims)
    match: dict = {
        "_company_id": company_id,
        "date": {"$gte": date_from, "$lte": date_to},
        **dim_filter,
    }

    # ── Total P&L KPIs ────────────────────────────────────────────────────────
    totals_docs = await col.aggregate([
        {"$match": match},
        {"$group": {
            "_id": None,
            "total_revenue": {"$sum": "$revenue"},
            "total_cogs": {"$sum": "$cogs"},
            "total_gross_profit": {"$sum": "$gross_profit"},
        }},
    ]).to_list(length=1)

    totals = totals_docs[0] if totals_docs else {}
    total_revenue: float = round(float(totals.get("total_revenue", 0.0)), 2)
    total_cogs: float = round(float(totals.get("total_cogs", 0.0)), 2)
    total_gross_profit: float = round(float(totals.get("total_gross_profit", 0.0)), 2)
    gross_margin: float = (
        round(total_gross_profit / total_revenue * 100, 2) if total_revenue > 0 else 0.0
    )

    # ── Revenue by category ───────────────────────────────────────────────────
    cat_docs = await col.aggregate([
        {"$match": match},
        {"$group": {"_id": "$category", "revenue": {"$sum": "$revenue"}}},
        {"$sort": {"revenue": -1}},
    ]).to_list(length=50)
    revenue_by_category = [
        CategoryRevenue(category=d["_id"] or "Other", revenue=round(float(d["revenue"]), 2))
        for d in cat_docs
    ]

    # ── Daily gross profit time-series ────────────────────────────────────────
    daily_docs = await col.aggregate([
        {"$match": match},
        {"$group": {"_id": "$date", "gross_profit": {"$sum": "$gross_profit"}}},
        {"$sort": {"_id": 1}},
    ]).to_list(length=365)
    daily_gross_profit = [
        DailyGrossProfit(date=d["_id"], gross_profit=round(float(d["gross_profit"]), 2))
        for d in daily_docs
    ]

    # ── Monthly revenue vs COGS ───────────────────────────────────────────────
    monthly_docs = await col.aggregate([
        {"$match": match},
        {"$group": {
            "_id": {"$substr": ["$date", 0, 7]},
            "revenue": {"$sum": "$revenue"},
            "cogs": {"$sum": "$cogs"},
        }},
        {"$sort": {"_id": 1}},
    ]).to_list(length=36)
    monthly_pnl = [
        MonthlyPnL(
            month=d["_id"],
            revenue=round(float(d["revenue"]), 2),
            cogs=round(float(d["cogs"]), 2),
        )
        for d in monthly_docs
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
                    "total_revenue": {"$sum": "$revenue"},
                    "total_cogs": {"$sum": "$cogs"},
                    "total_gross_profit": {"$sum": "$gross_profit"},
                }},
            ]).to_list(length=1)
            prev = prev_docs[0] if prev_docs else {}
            prev_rev = round(float(prev.get("total_revenue", 0.0)), 2)
            prev_gp = round(float(prev.get("total_gross_profit", 0.0)), 2)
            prev_gm = round(prev_gp / prev_rev * 100, 2) if prev_rev > 0 else 0.0
            deltas = {}
            for field, cur, prv in [
                ("total_revenue", total_revenue, prev_rev),
                ("total_gross_profit", total_gross_profit, prev_gp),
                ("gross_margin", gross_margin, prev_gm),
            ]:
                d = pct_delta(cur, prv)
                if d is not None:
                    deltas[field] = d

    result = FinanceKpisOut(
        total_revenue=total_revenue,
        total_cogs=total_cogs,
        total_gross_profit=total_gross_profit,
        gross_margin=gross_margin,
        revenue_by_category=revenue_by_category,
        daily_gross_profit=daily_gross_profit,
        monthly_pnl=monthly_pnl,
        deltas=deltas,
    )
    await set_json(_key, result.model_dump(), ANALYTICS_TTL)
    return result
