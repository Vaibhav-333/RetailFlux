"""Observability endpoints — API request metrics + Celery task stats (CEO/Admin only)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.dependencies import require_role
from app.domains.observability.service import (
    get_ai_usage_stats,
    get_cache_stats,
    get_celery_stats,
    get_observability_dashboard,
)
from app.models.user import User, UserRole
from app.schemas.cache import CacheStatsOut
from app.schemas.observability import AiUsageSummaryOut, CeleryStatsOut, ObservabilityDashboardOut

router = APIRouter()

_admin_dep = Depends(require_role(UserRole.CEO, UserRole.ADMIN))


@router.get(
    "/dashboard",
    response_model=ObservabilityDashboardOut,
    summary="API request metrics (CEO/Admin only)",
)
async def observability_dashboard(
    _: User = _admin_dep,
) -> ObservabilityDashboardOut:
    return await get_observability_dashboard()


@router.get(
    "/celery-stats",
    response_model=CeleryStatsOut,
    summary="Celery task execution stats last 24 h (CEO/Admin only)",
)
async def celery_stats(
    _: User = _admin_dep,
) -> CeleryStatsOut:
    return await get_celery_stats()


@router.get(
    "/cache-stats",
    response_model=CacheStatsOut,
    summary="Redis cache key counts by category (CEO/Admin only)",
)
async def cache_stats(
    _: User = _admin_dep,
) -> CacheStatsOut:
    return await get_cache_stats()


@router.get(
    "/ai-usage",
    response_model=AiUsageSummaryOut,
    summary="AI LLM usage summary for the last 24 h (CEO/Admin only)",
)
async def ai_usage(
    current_user: User = _admin_dep,
    db: AsyncSession = Depends(get_db),
) -> AiUsageSummaryOut:
    return await get_ai_usage_stats(db, current_user.company_id)
