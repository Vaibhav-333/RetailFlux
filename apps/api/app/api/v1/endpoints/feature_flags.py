"""Feature flag management endpoints (CEO/Admin only).

GET  /feature-flags        — list all flags visible to the company
PATCH /feature-flags/{key} — enable/disable a flag for the company
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel

from app.core.database import get_db
from app.core.feature_flags import is_enabled, list_flags, set_flag
from app.domains.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

_admin_dep = Depends(require_role(UserRole.CEO, UserRole.ADMIN))


class FeatureFlagOut(BaseModel):
    id: str
    company_id: Optional[str]
    key: str
    enabled: bool
    payload: Optional[Any]
    created_at: Optional[str]
    updated_at: Optional[str]


class FeatureFlagsResponse(BaseModel):
    flags: list[FeatureFlagOut]
    total: int


class FlagUpdate(BaseModel):
    enabled: bool
    payload: Optional[dict[str, Any]] = None


@router.get("", response_model=FeatureFlagsResponse, summary="List feature flags (CEO/Admin)")
async def get_feature_flags(
    current_user: User = _admin_dep,
    db: AsyncSession = Depends(get_db),
) -> FeatureFlagsResponse:
    flags = await list_flags(db, company_id=current_user.company_id)
    return FeatureFlagsResponse(
        flags=[FeatureFlagOut(**f) for f in flags],
        total=len(flags),
    )


@router.get(
    "/{key}/check",
    summary="Check if a single flag is enabled for the current user's company",
)
async def check_flag(
    key: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    enabled = await is_enabled(db, key, company_id=current_user.company_id)
    return {"key": key, "enabled": enabled}


@router.patch(
    "/{key}",
    summary="Enable or disable a feature flag for the current company (CEO/Admin)",
)
async def update_feature_flag(
    key: str,
    body: FlagUpdate = Body(...),
    current_user: User = _admin_dep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await set_flag(
        db,
        key=key,
        enabled=body.enabled,
        company_id=current_user.company_id,
        payload=body.payload,
    )
    return result
