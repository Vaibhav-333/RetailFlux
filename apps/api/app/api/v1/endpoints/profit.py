"""Predictive Profit Intelligence endpoints — Session 35."""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.domains.auth.dependencies import get_current_user
from app.domains.profit.attribution_service import get_profit_attribution
from app.domains.profit.forecast_service import get_profit_forecast
from app.domains.profit.levers_service import get_profit_levers
from app.models.user import User

router = APIRouter()


@router.get("/forecast")
async def profit_forecast(
    current_user: User = Depends(get_current_user),
) -> dict:
    """90-day gross-profit forecast with CI band (Holt-Winters)."""
    return await get_profit_forecast(company_id=str(current_user.company_id))


@router.get("/attribution")
async def profit_attribution(
    period: str = Query("28d", description="Current period: 7d, 28d, 90d"),
    compare_period: str = Query("prev_28d", description="Comparison period label"),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Waterfall decomposition of GP delta: Volume · Price · Mix · Cost · Promo."""
    return await get_profit_attribution(
        company_id=str(current_user.company_id),
        current_period=period,
        compare_period=compare_period,
    )


@router.get("/levers")
async def profit_levers(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Top-10 ranked action levers with simulated GP lift."""
    return await get_profit_levers(company_id=str(current_user.company_id))
