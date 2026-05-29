import math

from app.domains.analytics.summary_service import get_dashboard_summary
from app.schemas.analytics import DailyRevenue
from app.schemas.insights import AnomalyPoint


def detect_anomalies(
    daily_revenue: list[DailyRevenue],
    threshold: float = 2.0,
) -> list[AnomalyPoint]:
    """Z-score anomaly detection on daily revenue; flags |z| > threshold."""
    if len(daily_revenue) < 3:
        return []

    revenues = [d.revenue for d in daily_revenue]
    mean = sum(revenues) / len(revenues)
    variance = sum((r - mean) ** 2 for r in revenues) / len(revenues)
    std = math.sqrt(variance)

    if std == 0:
        return []

    return [
        AnomalyPoint(date=d.date, revenue=d.revenue, z_score=round((d.revenue - mean) / std, 2))
        for d in daily_revenue
        if abs((d.revenue - mean) / std) > threshold
    ]


async def get_revenue_anomalies(company_id: str) -> list[AnomalyPoint]:
    summary = await get_dashboard_summary(company_id)
    return detect_anomalies(summary.daily_revenue)
