"""Cache management endpoints — invalidation, warming, health (CEO/Admin only)."""
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.core.cache import delete_pattern, health_check, warm_analytics_cache
from app.domains.auth.dependencies import require_role
from app.models.user import User, UserRole
from app.schemas.cache import CacheHealth, CacheInvalidateResult, CacheWarmResult

router = APIRouter()

_admin_dep = Depends(require_role(UserRole.CEO, UserRole.ADMIN))

_DEPTS = {"sales", "marketing", "operations", "finance", "procurement"}


@router.delete(
    "/analytics",
    response_model=CacheInvalidateResult,
    summary="Invalidate analytics cache (CEO/Admin only)",
)
async def invalidate_analytics_cache(
    dept: Optional[str] = Query(None, description="Specific dept to flush, or omit for all"),
    warm: bool = Query(False, description="Pre-warm the cache after invalidation"),
    current_user: User = _admin_dep,
) -> CacheInvalidateResult:
    company = str(current_user.company_id)
    deleted = 0

    if dept and dept in _DEPTS:
        deleted += await delete_pattern(f"rf:cache:analytics:{dept}:{company}:*")
    elif dept is None:
        deleted += await delete_pattern(f"rf:cache:analytics:*:{company}:*")
        deleted += await delete_pattern(f"rf:cache:summary:{company}*")
        deleted += await delete_pattern(f"rf:cache:insights:{company}*")
        deleted += await delete_pattern(f"rf:cache:forecast:top-skus:{company}*")

    warmed = None
    if warm:
        warmed = await warm_analytics_cache(company)

    return CacheInvalidateResult(deleted=deleted, dept=dept, warmed=warmed)


@router.post(
    "/warm",
    response_model=CacheWarmResult,
    summary="Pre-warm analytics cache for the current company (CEO/Admin only)",
)
async def warm_cache(
    current_user: User = _admin_dep,
) -> CacheWarmResult:
    company = str(current_user.company_id)
    warmed = await warm_analytics_cache(company)
    return CacheWarmResult(company_id=company, warmed=warmed)


@router.get(
    "/health",
    response_model=CacheHealth,
    summary="Redis health check (CEO/Admin only)",
)
async def cache_health(
    _: User = _admin_dep,
) -> CacheHealth:
    data = await health_check()
    return CacheHealth(**data)
