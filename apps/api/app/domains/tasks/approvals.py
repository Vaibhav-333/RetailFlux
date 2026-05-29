"""Task approval workflow service.

Approval rules:
  - Any user can request an approval by naming an approver.
  - Only the designated approver can approve/reject.
  - CEO / Admin can approve any task regardless.
  - Every decision is recorded in task_activity for auditability.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskActivity, TaskApproval
from app.models.user import User


async def _get_task_or_404(
    db: AsyncSession, company_id: uuid.UUID, task_id: uuid.UUID
) -> Task:
    task = await db.scalar(
        select(Task).where(
            Task.id == task_id,
            Task.company_id == company_id,
            Task.deleted_at.is_(None),
        )
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


async def request_approval(
    db: AsyncSession,
    company_id: uuid.UUID,
    task_id: uuid.UUID,
    approver_id: uuid.UUID,
    requested_by: uuid.UUID,
) -> TaskApproval:
    """Create a pending approval request."""
    task = await _get_task_or_404(db, company_id, task_id)

    # Verify approver exists and belongs to same company
    approver = await db.scalar(
        select(User).where(User.id == approver_id, User.company_id == company_id)
    )
    if approver is None:
        raise HTTPException(status_code=404, detail="Approver not found")

    approval = TaskApproval(
        task_id=task.id,
        approver_id=approver_id,
        requested_by=requested_by,
    )
    db.add(approval)
    db.add(
        TaskActivity(
            task_id=task.id,
            user_id=requested_by,
            kind="assigned",
            new_value=f"approval_requested:{approver_id}",
        )
    )
    await db.commit()
    await db.refresh(approval)
    return approval


async def decide_approval(
    db: AsyncSession,
    company_id: uuid.UUID,
    approval_id: uuid.UUID,
    actor_id: uuid.UUID,
    actor_role: str,
    decision: str,
    note: Optional[str] = None,
) -> TaskApproval:
    """Approve or reject a pending approval.  Only the named approver (or CEO/Admin) can decide."""
    if decision not in ("approved", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="decision must be 'approved' or 'rejected'",
        )

    approval = await db.scalar(
        select(TaskApproval)
        .join(Task, Task.id == TaskApproval.task_id)
        .where(TaskApproval.id == approval_id, Task.company_id == company_id)
    )
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.decision is not None:
        raise HTTPException(status_code=409, detail="Approval already decided")

    is_admin = actor_role in ("ceo", "admin")
    if not is_admin and approval.approver_id != actor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the designated approver can decide",
        )

    approval.decision = decision
    approval.note = note
    approval.decided_at = datetime.now(timezone.utc)

    task = await db.get(Task, approval.task_id)
    if task:
        db.add(
            TaskActivity(
                task_id=task.id,
                user_id=actor_id,
                kind="status_changed",
                old_value="pending_approval",
                new_value=decision,
            )
        )

    await db.commit()
    await db.refresh(approval)
    return approval


async def list_pending_approvals(
    db: AsyncSession,
    company_id: uuid.UUID,
    approver_id: uuid.UUID,
    *,
    page: int = 1,
    size: int = 25,
) -> tuple[list[TaskApproval], int]:
    """Return pending approvals for a user (where they are the named approver)."""
    from sqlalchemy import func  # noqa: PLC0415
    q = (
        select(TaskApproval)
        .join(Task, Task.id == TaskApproval.task_id)
        .where(
            Task.company_id == company_id,
            TaskApproval.approver_id == approver_id,
            TaskApproval.decision.is_(None),
        )
    )
    total: int = await db.scalar(select(func.count()).select_from(q.subquery())) or 0
    items = list(
        (await db.scalars(q.order_by(TaskApproval.created_at.asc()).offset((page - 1) * size).limit(size))).all()
    )
    return items, total


async def list_task_approvals(
    db: AsyncSession,
    company_id: uuid.UUID,
    task_id: uuid.UUID,
) -> list[TaskApproval]:
    task = await _get_task_or_404(db, company_id, task_id)
    approvals = list(
        (
            await db.scalars(
                select(TaskApproval)
                .where(TaskApproval.task_id == task.id)
                .order_by(TaskApproval.created_at.asc())
            )
        ).all()
    )
    return approvals
