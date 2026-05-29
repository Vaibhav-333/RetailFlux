from fastapi import APIRouter, Depends, Query

from app.domains.auth.dependencies import get_current_user
from app.domains.forecasting.forecast_service import get_sku_forecast
from app.domains.forecasting.top_skus_forecast import get_top_skus_forecast
from app.models.user import User
from app.schemas.forecast import ForecastOut, SkuForecast

router = APIRouter()


@router.get("/top-skus", response_model=ForecastOut)
async def top_skus_forecast(
    current_user: User = Depends(get_current_user),
) -> ForecastOut:
    return await get_top_skus_forecast(company_id=str(current_user.company_id))


@router.get("/sku", response_model=SkuForecast)
async def sku_forecast(
    sku: str = Query(..., description="SKU identifier e.g. BLZ-BLK-M"),
    current_user: User = Depends(get_current_user),
) -> SkuForecast:
    return await get_sku_forecast(
        company_id=str(current_user.company_id),
        sku=sku,
    )
