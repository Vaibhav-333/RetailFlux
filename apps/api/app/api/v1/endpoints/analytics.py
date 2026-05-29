"""Analytics endpoints with department-level RBAC enforcement.

Each endpoint requires the user's role to have access to that specific department.
CEO and ADMIN can access all departments. Dept-specific roles can only access their own.

Session 26: added compare_to (previous_period | previous_year) and dims query params
to every endpoint for a consistent contract.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.domains.analytics.finance_service import get_finance_kpis
from app.domains.analytics.marketing_service import get_marketing_kpis
from app.domains.analytics.operations_service import get_operations_kpis
from app.domains.analytics.procurement_service import get_procurement_kpis
from app.domains.analytics.sales_service import get_sales_kpis
from app.domains.analytics.summary_service import get_dashboard_summary
from app.domains.auth.dependencies import require_dept_access
from app.models.user import User
from app.schemas.analytics import (
    DashboardSummaryOut,
    FinanceKpisOut,
    MarketingKpisOut,
    OperationsKpisOut,
    ProcurementKpisOut,
    SalesKpisOut,
)

router = APIRouter()


@router.get("/sales", response_model=SalesKpisOut)
async def sales_analytics(
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    compare_to: Optional[str] = Query(None, description="previous_period | previous_year"),
    dims: Optional[str] = Query(None, description="Comma-separated dim=value pairs, e.g. region=North"),
    current_user: User = Depends(require_dept_access("sales")),
) -> SalesKpisOut:
    return await get_sales_kpis(
        company_id=str(current_user.company_id),
        date_from=date_from,
        date_to=date_to,
        compare_to=compare_to,
        dims=dims,
    )


@router.get("/marketing", response_model=MarketingKpisOut)
async def marketing_analytics(
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    compare_to: Optional[str] = Query(None, description="previous_period | previous_year"),
    dims: Optional[str] = Query(None, description="Comma-separated dim=value pairs"),
    current_user: User = Depends(require_dept_access("marketing")),
) -> MarketingKpisOut:
    return await get_marketing_kpis(
        company_id=str(current_user.company_id),
        date_from=date_from,
        date_to=date_to,
        compare_to=compare_to,
        dims=dims,
    )


@router.get("/operations", response_model=OperationsKpisOut)
async def operations_analytics(
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    compare_to: Optional[str] = Query(None, description="previous_period | previous_year"),
    dims: Optional[str] = Query(None, description="Comma-separated dim=value pairs"),
    current_user: User = Depends(require_dept_access("operations")),
) -> OperationsKpisOut:
    return await get_operations_kpis(
        company_id=str(current_user.company_id),
        date_from=date_from,
        date_to=date_to,
        compare_to=compare_to,
        dims=dims,
    )


@router.get("/finance", response_model=FinanceKpisOut)
async def finance_analytics(
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    compare_to: Optional[str] = Query(None, description="previous_period | previous_year"),
    dims: Optional[str] = Query(None, description="Comma-separated dim=value pairs"),
    current_user: User = Depends(require_dept_access("finance")),
) -> FinanceKpisOut:
    return await get_finance_kpis(
        company_id=str(current_user.company_id),
        date_from=date_from,
        date_to=date_to,
        compare_to=compare_to,
        dims=dims,
    )


@router.get("/procurement", response_model=ProcurementKpisOut)
async def procurement_analytics(
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    compare_to: Optional[str] = Query(None, description="previous_period | previous_year"),
    dims: Optional[str] = Query(None, description="Comma-separated dim=value pairs"),
    current_user: User = Depends(require_dept_access("procurement")),
) -> ProcurementKpisOut:
    return await get_procurement_kpis(
        company_id=str(current_user.company_id),
        date_from=date_from,
        date_to=date_to,
        compare_to=compare_to,
        dims=dims,
    )


@router.get("/summary", response_model=DashboardSummaryOut)
async def dashboard_summary(
    current_user: User = Depends(require_dept_access("summary")),
) -> DashboardSummaryOut:
    return await get_dashboard_summary(company_id=str(current_user.company_id))
