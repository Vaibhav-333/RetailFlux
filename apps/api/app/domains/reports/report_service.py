import csv
import io
import json
from typing import Literal

from app.domains.analytics.finance_service import get_finance_kpis
from app.domains.analytics.marketing_service import get_marketing_kpis
from app.domains.analytics.operations_service import get_operations_kpis
from app.domains.analytics.procurement_service import get_procurement_kpis
from app.domains.analytics.sales_service import get_sales_kpis
from app.schemas.analytics import (
    FinanceKpisOut,
    MarketingKpisOut,
    OperationsKpisOut,
    ProcurementKpisOut,
    SalesKpisOut,
)

DeptLiteral = Literal["sales", "marketing", "operations", "finance", "procurement"]

_KpisType = SalesKpisOut | MarketingKpisOut | OperationsKpisOut | FinanceKpisOut | ProcurementKpisOut


async def export_report(
    company_id: str,
    dept: DeptLiteral,
    date_from: str | None,
    date_to: str | None,
    fmt: Literal["csv", "json"],
) -> tuple[bytes, str]:
    """Return (content_bytes, filename) for the requested department export."""
    kpis = await _fetch_kpis(company_id, dept, date_from, date_to)
    date_tag = date_from or "all"
    filename = f"retailflux_{dept}_{date_tag}.{fmt}"

    if fmt == "json":
        return kpis.model_dump_json(indent=2).encode(), filename

    rows = _primary_series(dept, kpis)
    return _to_csv(rows), filename


async def _fetch_kpis(
    company_id: str,
    dept: DeptLiteral,
    date_from: str | None,
    date_to: str | None,
) -> _KpisType:
    if dept == "sales":
        return await get_sales_kpis(company_id, date_from, date_to)
    if dept == "marketing":
        return await get_marketing_kpis(company_id, date_from, date_to)
    if dept == "operations":
        return await get_operations_kpis(company_id, date_from, date_to)
    if dept == "finance":
        return await get_finance_kpis(company_id, date_from, date_to)
    return await get_procurement_kpis(company_id, date_from, date_to)


def _primary_series(dept: DeptLiteral, kpis: _KpisType) -> list[dict]:
    """Extract the most useful flat list for CSV export."""
    if dept == "sales" and isinstance(kpis, SalesKpisOut):
        return [r.model_dump() for r in kpis.daily_revenue]
    if dept == "marketing" and isinstance(kpis, MarketingKpisOut):
        return [r.model_dump() for r in kpis.daily_spend]
    if dept == "operations" and isinstance(kpis, OperationsKpisOut):
        return [r.model_dump() for r in kpis.daily_stock_level]
    if dept == "finance" and isinstance(kpis, FinanceKpisOut):
        return [r.model_dump() for r in kpis.monthly_pnl]
    if dept == "procurement" and isinstance(kpis, ProcurementKpisOut):
        return [r.model_dump() for r in kpis.daily_spend]
    return []


def _to_csv(rows: list[dict]) -> bytes:
    if not rows:
        return b""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode()
