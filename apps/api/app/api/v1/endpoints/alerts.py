"""Alert preferences and manual check endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.alerts.alert_service import (
    check_and_send_alerts,
    get_alert_prefs,
    update_alert_prefs,
)
from app.domains.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.alerts import AlertCheckResult, AlertPrefsOut, AlertPrefsUpdate

router = APIRouter()


@router.get("/preferences", response_model=AlertPrefsOut)
async def get_preferences(
    current_user: User = Depends(get_current_user),
) -> AlertPrefsOut:
    return await get_alert_prefs(current_user.id)


@router.patch("/preferences", response_model=AlertPrefsOut)
async def patch_preferences(
    body: AlertPrefsUpdate,
    current_user: User = Depends(get_current_user),
) -> AlertPrefsOut:
    return await update_alert_prefs(current_user.id, body)


@router.post("/check", response_model=AlertCheckResult)
async def check_alerts(
    current_user: User = Depends(require_role(UserRole.CEO, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> AlertCheckResult:
    """Trigger an immediate company-wide alert check (CEO/Admin only)."""
    return await check_and_send_alerts(current_user.company_id, db)
