import asyncio

from app.core.cache import ANALYTICS_TTL, get_json, set_json, summary_key
from app.domains.analytics.finance_service import get_finance_kpis
from app.domains.analytics.marketing_service import get_marketing_kpis
from app.domains.analytics.operations_service import get_operations_kpis
from app.domains.analytics.procurement_service import get_procurement_kpis
from app.domains.analytics.sales_service import get_sales_kpis
from app.schemas.analytics import DashboardSummaryOut


async def get_dashboard_summary(company_id: str) -> DashboardSummaryOut:
    _key = summary_key(company_id)
    _hit = await get_json(_key)
    if _hit:
        return DashboardSummaryOut(**_hit)

    results = await asyncio.gather(
        get_sales_kpis(company_id),
        get_marketing_kpis(company_id),
        get_operations_kpis(company_id),
        get_finance_kpis(company_id),
        get_procurement_kpis(company_id),
        return_exceptions=True,
    )

    sales, mkt, ops, fin, proc = results

    total_revenue = float(sales.total_revenue) if not isinstance(sales, Exception) else 0.0
    top_sku = sales.top_sku if not isinstance(sales, Exception) else None
    daily_revenue = sales.daily_revenue if not isinstance(sales, Exception) else []

    roas = float(mkt.roas) if not isinstance(mkt, Exception) else 0.0
    marketing_spend = float(mkt.total_spend) if not isinstance(mkt, Exception) else 0.0

    skus_below_reorder = int(ops.skus_below_reorder) if not isinstance(ops, Exception) else 0
    active_warehouses = int(ops.active_warehouses) if not isinstance(ops, Exception) else 0

    gross_margin = float(fin.gross_margin) if not isinstance(fin, Exception) else 0.0
    total_gross_profit = float(fin.total_gross_profit) if not isinstance(fin, Exception) else 0.0

    procurement_spend = float(proc.total_spend) if not isinstance(proc, Exception) else 0.0
    unique_suppliers = int(proc.unique_suppliers) if not isinstance(proc, Exception) else 0
    avg_lead_days = float(proc.avg_lead_days) if not isinstance(proc, Exception) else 0.0

    result = DashboardSummaryOut(
        total_revenue=total_revenue,
        top_sku=top_sku,
        roas=roas,
        marketing_spend=marketing_spend,
        skus_below_reorder=skus_below_reorder,
        active_warehouses=active_warehouses,
        gross_margin=gross_margin,
        total_gross_profit=total_gross_profit,
        procurement_spend=procurement_spend,
        unique_suppliers=unique_suppliers,
        avg_lead_days=avg_lead_days,
        daily_revenue=daily_revenue,
    )
    await set_json(_key, result.model_dump(), ANALYTICS_TTL)
    return result
