"""Dynamic Pricing recommendations endpoints — Session 35."""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.domains.auth.dependencies import get_current_user
from app.domains.pricing.suggestions_service import (
    get_pricing_suggestions,
    get_pricing_summary,
    refresh_pricing_suggestions,
)
from app.models.user import User, UserRole

router = APIRouter()


@router.get("/suggestions")
async def pricing_suggestions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    direction: Optional[str] = Query(None, description="Filter: 'increase' or 'decrease'"),
    min_lift: Optional[float] = Query(None, description="Min expected lift %"),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Paginated per-SKU price suggestions with elasticity-based lift estimates."""
    return await get_pricing_suggestions(
        company_id=str(current_user.company_id),
        page=page,
        page_size=page_size,
        direction=direction,
        min_lift=min_lift,
    )


@router.get("/summary")
async def pricing_summary(
    current_user: User = Depends(get_current_user),
) -> dict:
    """High-level summary of the current pricing opportunity."""
    return await get_pricing_summary(company_id=str(current_user.company_id))


@router.post("/refresh")
async def refresh_suggestions(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Trigger on-demand recompute of pricing suggestions (CEO/Admin/Finance only)."""
    if current_user.role not in (UserRole.CEO, UserRole.ADMIN, UserRole.FINANCE):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="CEO, Admin, or Finance required")
    count = await refresh_pricing_suggestions(company_id=str(current_user.company_id))
    return {"refreshed": count, "status": "ok"}
