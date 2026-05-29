from datetime import date, timedelta
from typing import Optional

from app.core.cache import ANALYTICS_TTL, analytics_key, get_json, set_json
from app.core.mongodb import get_mongo_db
from app.domains.analytics.utils import compute_compare_period, parse_dims, pct_delta
from app.schemas.analytics import (
    CampaignKpis,
    CampaignSpend,
    DailySpend,
    MarketingKpisOut,
)


async def get_marketing_kpis(
    company_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    compare_to: Optional[str] = None,
    dims: Optional[str] = None,
) -> MarketingKpisOut:
    if not date_from:
        date_from = (date.today() - timedelta(days=90)).isoformat()
    if not date_to:
        date_to = date.today().isoformat()

    _key = analytics_key("marketing", company_id, date_from, date_to)
    if compare_to or dims:
        _key += f":{compare_to or ''}:{dims or ''}"

    _hit = await get_json(_key)
    if _hit:
        return MarketingKpisOut(**_hit)

    db = get_mongo_db()
    mkt_col = db["staging_marketing"]
    sales_col = db["staging_sales"]

    dim_filter = parse_dims(dims)
    match: dict = {
        "_company_id": company_id,
        "date": {"$gte": date_from, "$lte": date_to},
        **dim_filter,
    }

    # ── Total marketing KPIs ──────────────────────────────────────────────────
    totals_docs = await mkt_col.aggregate([
        {"$match": match},
        {"$group": {
            "_id": None,
            "total_spend": {"$sum": "$spend"},
            "total_conversions": {"$sum": "$conversions"},
            "total_impressions": {"$sum": "$impressions"},
            "total_clicks": {"$sum": "$clicks"},
        }},
    ]).to_list(length=1)

    totals = totals_docs[0] if totals_docs else {}
    total_spend = float(totals.get("total_spend", 0.0))
    total_conversions = int(totals.get("total_conversions", 0))
    total_impressions = int(totals.get("total_impressions", 0))
    total_clicks = int(totals.get("total_clicks", 0))

    ctr = round(total_clicks / total_impressions * 100, 2) if total_impressions > 0 else 0.0
    cac = round(total_spend / total_conversions, 2) if total_conversions > 0 else 0.0

    # ── ROAS: pull revenue from staging_sales for the same window ─────────────
    rev_docs = await sales_col.aggregate([
        {"$match": match},
        {"$group": {"_id": None, "total_revenue": {"$sum": "$revenue"}}},
    ]).to_list(length=1)
    total_revenue = float(rev_docs[0]["total_revenue"]) if rev_docs else 0.0
    roas = round(total_revenue / total_spend, 2) if total_spend > 0 else 0.0

    # ── Top 10 campaigns by conversions ───────────────────────────────────────
    campaign_docs = await mkt_col.aggregate([
        {"$match": match},
        {"$group": {"_id": "$campaign_id", "conversions": {"$sum": "$conversions"}}},
        {"$sort": {"conversions": -1}},
        {"$limit": 10},
    ]).to_list(length=10)
    top_campaigns = [
        CampaignKpis(campaign_id=d["_id"], conversions=int(d["conversions"]))
        for d in campaign_docs
    ]

    # ── Daily spend time-series ───────────────────────────────────────────────
    daily_docs = await mkt_col.aggregate([
        {"$match": match},
        {"$group": {"_id": "$date", "spend": {"$sum": "$spend"}}},
        {"$sort": {"_id": 1}},
    ]).to_list(length=365)
    daily_spend = [
        DailySpend(date=d["_id"], spend=round(float(d["spend"]), 2))
        for d in daily_docs
    ]

    # ── Spend by campaign (top 10 for pie chart) ──────────────────────────────
    pie_docs = await mkt_col.aggregate([
        {"$match": match},
        {"$group": {"_id": "$campaign_id", "spend": {"$sum": "$spend"}}},
        {"$sort": {"spend": -1}},
        {"$limit": 10},
    ]).to_list(length=10)
    spend_by_campaign = [
        CampaignSpend(campaign_id=d["_id"], spend=round(float(d["spend"]), 2))
        for d in pie_docs
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
            prev_mkt = await mkt_col.aggregate([
                {"$match": prev_match},
                {"$group": {
                    "_id": None,
                    "total_spend": {"$sum": "$spend"},
                    "total_conversions": {"$sum": "$conversions"},
                    "total_impressions": {"$sum": "$impressions"},
                    "total_clicks": {"$sum": "$clicks"},
                }},
            ]).to_list(length=1)
            prev_rev = await sales_col.aggregate([
                {"$match": prev_match},
                {"$group": {"_id": None, "total_revenue": {"$sum": "$revenue"}}},
            ]).to_list(length=1)
            pm = prev_mkt[0] if prev_mkt else {}
            prev_spend = float(pm.get("total_spend", 0.0))
            prev_convs = int(pm.get("total_conversions", 0))
            prev_imps = int(pm.get("total_impressions", 0))
            prev_clicks = int(pm.get("total_clicks", 0))
            prev_revenue = float(prev_rev[0]["total_revenue"]) if prev_rev else 0.0
            prev_roas = round(prev_revenue / prev_spend, 2) if prev_spend > 0 else 0.0
            prev_ctr = round(prev_clicks / prev_imps * 100, 2) if prev_imps > 0 else 0.0
            prev_cac = round(prev_spend / prev_convs, 2) if prev_convs > 0 else 0.0
            deltas = {}
            for field, cur, prv in [
                ("total_spend", total_spend, prev_spend),
                ("total_conversions", float(total_conversions), float(prev_convs)),
                ("roas", roas, prev_roas),
                ("ctr", ctr, prev_ctr),
                ("cac", cac, prev_cac),
            ]:
                d = pct_delta(cur, prv)
                if d is not None:
                    deltas[field] = d

    result = MarketingKpisOut(
        total_spend=round(total_spend, 2),
        total_conversions=total_conversions,
        total_impressions=total_impressions,
        ctr=ctr,
        roas=roas,
        cac=cac,
        top_campaigns=top_campaigns,
        spend_by_campaign=spend_by_campaign,
        daily_spend=daily_spend,
        deltas=deltas,
    )
    await set_json(_key, result.model_dump(), ANALYTICS_TTL)
    return result
