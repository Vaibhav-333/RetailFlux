"""Task CRUD + workflow service layer."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import delete as sa_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.event_log import record_event
from app.domains.tasks.workflow import can_transition
from app.models.task import Task, TaskActivity, TaskAssignee, TaskComment, TaskDepartment
from app.schemas.task import (
    TaskAssignRequest,
    TaskCommentCreate,
    TaskCreate,
    TaskTransition,
    TaskUpdate,
)

log = logging.getLogger(__name__)

# ── Loader helpers ─────────────────────────────────────────────────────────────


def _base_opts() -> list:
    """Eagerly load assignees + departments (used by list + brief endpoints)."""
    return [selectinload(Task.assignees), selectinload(Task.departments)]


def _detail_opts() -> list:
    """Eagerly load all relationships (used by get_task and post-mutation fetches)."""
    return [
        selectinload(Task.assignees),
        selectinload(Task.departments),
        selectinload(Task.activity),
        selectinload(Task.comments),
    ]


async def _get_or_404(
    db: AsyncSession,
    company_id: uuid.UUID,
    task_id: uuid.UUID,
    *,
    detail: bool = False,
) -> Task:
    opts = _detail_opts() if detail else _base_opts()
    task = await db.scalar(
        select(Task)
        .options(*opts)
        .where(
            Task.id == task_id,
            Task.company_id == company_id,
            Task.deleted_at.is_(None),
        )
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


async def _record_activity(
    db: AsyncSession,
    task_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    kind: str,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
) -> None:
    db.add(
        TaskActivity(
            task_id=task_id,
            user_id=user_id,
            kind=kind,
            old_value=old_value,
            new_value=new_value,
        )
    )


# ── CRUD ───────────────────────────────────────────────────────────────────────


async def list_tasks(
    db: AsyncSession,
    company_id: uuid.UUID,
    *,
    status: Optional[str] = None,
    assignee_id: Optional[uuid.UUID] = None,
    page: int = 1,
    size: int = 25,
) -> tuple[list[Task], int]:
    q = (
        select(Task)
        .options(*_base_opts())
        .where(Task.company_id == company_id, Task.deleted_at.is_(None))
    )
    if status:
        q = q.where(Task.status == status)
    if assignee_id:
        q = q.join(Task.assignees).where(TaskAssignee.user_id == assignee_id)

    total: int = await db.scalar(select(func.count()).select_from(q.subquery())) or 0
    tasks = list((await db.scalars(q.offset((page - 1) * size).limit(size))).all())
    return tasks, total


async def create_task(
    db: AsyncSession,
    company_id: uuid.UUID,
    actor_id: uuid.UUID,
    data: TaskCreate,
) -> Task:
    task = Task(
        company_id=company_id,
        title=data.title,
        description=data.description,
        priority=data.priority,
        task_type=data.task_type,
        source=data.source,
        due_at=data.due_at,
        sla_hours=data.sla_hours,
        task_metadata=data.task_metadata,
        created_by=actor_id,
    )
    db.add(task)
    await db.flush()  # populate task.id before FKs

    for dept in data.departments:
        db.add(TaskDepartment(task_id=task.id, department=dept))
    for uid in data.assignee_ids:
        db.add(TaskAssignee(task_id=task.id, user_id=uid, role_in_task="collaborator"))

    await _record_activity(db, task.id, actor_id, "created", new_value=data.title)
    await db.commit()

    # Re-fetch with all relationships populated
    task = await _get_or_404(db, company_id, task.id)
    try:
        from app.core.pubsub import publish_event  # lazy import avoids circular deps
        await publish_event(str(company_id), {"type": "task_created", "task_id": str(task.id)})
    except Exception:
        log.warning("Failed to publish task_created event")
    # Event log — fire-and-forget, uses its own session
    asyncio.ensure_future(record_event(
        db,
        company_id=company_id,
        kind="task.created",
        payload={"title": task.title, "priority": task.priority, "source": task.source},
        actor_id=actor_id,
        resource_type="task",
        resource_id=task.id,
    ))
    return task


async def get_task(
    db: AsyncSession, company_id: uuid.UUID, task_id: uuid.UUID
) -> Task:
    return await _get_or_404(db, company_id, task_id, detail=True)


async def update_task(
    db: AsyncSession,
    company_id: uuid.UUID,
    task_id: uuid.UUID,
    data: TaskUpdate,
    actor_id: uuid.UUID,
) -> Task:
    task = await _get_or_404(db, company_id, task_id)

    if data.title is not None:
        task.title = data.title
    if data.description is not None:
        task.description = data.description
    if data.priority is not None:
        task.priority = data.priority
    if data.task_type is not None:
        task.task_type = data.task_type
    if data.due_at is not None:
        task.due_at = data.due_at
    if data.sla_hours is not None:
        task.sla_hours = data.sla_hours
    if data.task_metadata is not None:
        task.task_metadata = data.task_metadata

    if data.departments is not None:
        await db.execute(sa_delete(TaskDepartment).where(TaskDepartment.task_id == task.id))
        for dept in data.departments:
            db.add(TaskDepartment(task_id=task.id, department=dept))

    task.updated_at = datetime.now(timezone.utc)
    await _record_activity(db, task.id, actor_id, "kpi_updated")
    await db.commit()
    return await _get_or_404(db, company_id, task_id)


async def delete_task(
    db: AsyncSession,
    company_id: uuid.UUID,
    task_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> None:
    task = await _get_or_404(db, company_id, task_id)
    task.deleted_at = datetime.now(timezone.utc)
    await _record_activity(
        db, task.id, actor_id, "status_changed",
        old_value=task.status, new_value="deleted",
    )
    await db.commit()
    asyncio.ensure_future(record_event(
        db,
        company_id=company_id,
        kind="task.deleted",
        payload={"title": task.title},
        actor_id=actor_id,
        resource_type="task",
        resource_id=task_id,
    ))


async def transition_task(
    db: AsyncSession,
    company_id: uuid.UUID,
    task_id: uuid.UUID,
    data: TaskTransition,
    actor_id: uuid.UUID,
) -> Task:
    task = await _get_or_404(db, company_id, task_id)
    if not can_transition(task.status, data.to_status):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot transition from '{task.status}' to '{data.to_status}'",
        )
    old_status = task.status
    task.status = data.to_status
    task.updated_at = datetime.now(timezone.utc)
    await _record_activity(
        db, task.id, actor_id, "status_changed",
        old_value=old_status, new_value=data.to_status,
    )
    await db.commit()
    try:
        from app.core.pubsub import publish_event
        await publish_event(
            str(company_id),
            {"type": "task_updated", "task_id": str(task_id), "status": data.to_status},
        )
    except Exception:
        log.warning("Failed to publish task_updated event")
    asyncio.ensure_future(record_event(
        db,
        company_id=company_id,
        kind="task.status_changed",
        payload={"from": old_status, "to": data.to_status},
        actor_id=actor_id,
        resource_type="task",
        resource_id=task_id,
    ))
    return await _get_or_404(db, company_id, task_id)


async def assign_task(
    db: AsyncSession,
    company_id: uuid.UUID,
    task_id: uuid.UUID,
    data: TaskAssignRequest,
    actor_id: uuid.UUID,
) -> Task:
    task = await _get_or_404(db, company_id, task_id)
    existing = await db.scalar(
        select(TaskAssignee).where(
            TaskAssignee.task_id == task.id,
            TaskAssignee.user_id == data.user_id,
        )
    )
    if existing:
        existing.role_in_task = data.role_in_task
    else:
        db.add(TaskAssignee(task_id=task.id, user_id=data.user_id, role_in_task=data.role_in_task))
        await _record_activity(db, task.id, actor_id, "assigned", new_value=str(data.user_id))
    await db.commit()
    return await _get_or_404(db, company_id, task_id)


async def remove_assignee(
    db: AsyncSession,
    company_id: uuid.UUID,
    task_id: uuid.UUID,
    user_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> Task:
    await _get_or_404(db, company_id, task_id)
    assignee = await db.scalar(
        select(TaskAssignee).where(
            TaskAssignee.task_id == task_id,
            TaskAssignee.user_id == user_id,
        )
    )
    if assignee:
        await db.delete(assignee)
        await db.commit()
    return await _get_or_404(db, company_id, task_id)


async def add_comment(
    db: AsyncSession,
    company_id: uuid.UUID,
    task_id: uuid.UUID,
    actor_id: uuid.UUID,
    data: TaskCommentCreate,
) -> TaskComment:
    task = await _get_or_404(db, company_id, task_id)
    comment = TaskComment(task_id=task.id, user_id=actor_id, body=data.body)
    db.add(comment)
    await _record_activity(db, task.id, actor_id, "commented")
    await db.commit()
    await db.refresh(comment)
    return comment


async def get_activity(
    db: AsyncSession,
    task_id: uuid.UUID,
    page: int = 1,
    size: int = 25,
) -> tuple[list[TaskActivity], int]:
    q = (
        select(TaskActivity)
        .where(TaskActivity.task_id == task_id)
        .order_by(TaskActivity.created_at.desc())
    )
    total: int = await db.scalar(select(func.count()).select_from(q.subquery())) or 0
    items = list((await db.scalars(q.offset((page - 1) * size).limit(size))).all())
    return items, total
