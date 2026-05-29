import json

from app.core.cache import INSIGHTS_TTL, get_json, insights_key, set_json
from app.core.gemini import generate_text
from app.domains.analytics.summary_service import get_dashboard_summary
from app.schemas.insights import InsightItem, InsightsOut


def _build_prompt(summary) -> str:
    return (
        "You are RetailFlux AI, an expert retail analytics assistant for a fashion company.\n\n"
        "Here are the latest 90-day KPIs:\n"
        f"- Sales: Revenue ${summary.total_revenue:,.0f}, Top SKU: {summary.top_sku or 'N/A'}\n"
        f"- Marketing: ROAS {summary.roas:.2f}x, Ad Spend ${summary.marketing_spend:,.0f}\n"
        f"- Operations: {summary.skus_below_reorder} SKUs below reorder, "
        f"{summary.active_warehouses} active warehouses\n"
        f"- Finance: Gross Margin {summary.gross_margin:.1f}%, "
        f"Gross Profit ${summary.total_gross_profit:,.0f}\n"
        f"- Procurement: Spend ${summary.procurement_spend:,.0f}, "
        f"{summary.unique_suppliers} suppliers, avg {summary.avg_lead_days:.1f}-day lead time\n\n"
        "Return a JSON object with this exact structure:\n"
        '{"summary": "2-3 sentence executive summary of overall business health",\n'
        ' "insights": [\n'
        '   {"dept": "sales", "text": "one concise insight sentence"},\n'
        '   {"dept": "marketing", "text": "one concise insight sentence"},\n'
        '   {"dept": "operations", "text": "one concise insight sentence"},\n'
        '   {"dept": "finance", "text": "one concise insight sentence"},\n'
        '   {"dept": "procurement", "text": "one concise insight sentence"}\n'
        " ]}\n"
        "Return only valid JSON, no markdown code fences."
    )


async def generate_insights(company_id: str) -> InsightsOut:
    _key = insights_key(company_id)
    _hit = await get_json(_key)
    if _hit:
        return InsightsOut(**_hit)

    summary = await get_dashboard_summary(company_id)
    prompt = _build_prompt(summary)
    raw_text, provider = await generate_text(prompt)

    try:
        # Strip any accidental markdown fences
        clean = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = json.loads(clean)
        exec_summary: str = parsed.get("summary", raw_text)
        insights = [
            InsightItem(dept=item["dept"], text=item["text"])
            for item in parsed.get("insights", [])
        ]
    except (json.JSONDecodeError, KeyError, TypeError):
        exec_summary = raw_text
        insights = []

    result = InsightsOut(summary=exec_summary, insights=insights, generated_by=provider)
    await set_json(_key, result.model_dump(), INSIGHTS_TTL)
    return result
