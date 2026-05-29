from typing import Optional

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.schemas.audit import AuditLogEntry, AuditLogsResponse


async def list_audit_logs(
    db: AsyncSession,
    page: int = 1,
    size: int = 20,
    resource: Optional[str] = None,
    action: Optional[str] = None,
    sort: str = "created_at:desc",
) -> AuditLogsResponse:
    base_q = select(AuditLog)
    if resource:
        base_q = base_q.where(AuditLog.resource == resource)
    if action:
        base_q = base_q.where(AuditLog.action == action.upper())

    total: int = await db.scalar(
        select(func.count()).select_from(base_q.subquery())
    ) or 0

    sort_key, _, sort_dir = sort.partition(":")
    allowed_keys = {"created_at", "resource", "action"}
    col = getattr(AuditLog, sort_key if sort_key in allowed_keys else "created_at")
    order = asc(col) if sort_dir == "asc" else desc(col)

    rows = await db.scalars(
        base_q.order_by(order)
        .offset((page - 1) * size)
        .limit(size)
    )
    items = [
        AuditLogEntry(
            id=str(r.id),
            user_id=str(r.user_id) if r.user_id else None,
            action=r.action,
            resource=r.resource,
            resource_id=r.resource_id,
            ip=r.ip,
            ua=r.ua,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in rows.all()
    ]
    filters: dict[str, str] = {}
    if resource:
        filters["resource"] = resource
    if action:
        filters["action"] = action
    return AuditLogsResponse(items=items, total=total, page=page, pageSize=size, sort=sort, filters=filters)
