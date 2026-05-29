"""Audit log endpoint — paginated history of mutating API actions (CEO/Admin only)."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.audit.service import list_audit_logs
from app.domains.auth.dependencies import require_role
from app.models.user import User, UserRole
from app.schemas.audit import AuditLogsResponse

router = APIRouter()


@router.get(
    "/logs",
    response_model=AuditLogsResponse,
    summary="Paginated audit log (CEO/Admin only)",
)
async def get_audit_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    resource: Optional[str] = Query(None, description="Filter by resource (e.g. 'users')"),
    action: Optional[str] = Query(None, description="Filter by HTTP method (e.g. 'POST')"),
    sort: str = Query("created_at:desc", description="Sort as field:asc|desc"),
    _current_user: User = Depends(require_role(UserRole.CEO, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> AuditLogsResponse:
    return await list_audit_logs(db, page=page, size=size, resource=resource, action=action, sort=sort)
