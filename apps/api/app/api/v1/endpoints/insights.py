from fastapi import APIRouter, Depends

from app.domains.auth.dependencies import get_current_user
from app.domains.insights.anomaly_service import get_revenue_anomalies
from app.domains.insights.insight_service import generate_insights
from app.models.user import User
from app.schemas.insights import AnomalyPoint, InsightsOut

router = APIRouter()


@router.get("/summary", response_model=InsightsOut)
async def insights_summary(
    current_user: User = Depends(get_current_user),
) -> InsightsOut:
    return await generate_insights(company_id=str(current_user.company_id))


@router.get("/anomalies", response_model=list[AnomalyPoint])
async def revenue_anomalies(
    current_user: User = Depends(get_current_user),
) -> list[AnomalyPoint]:
    return await get_revenue_anomalies(company_id=str(current_user.company_id))
