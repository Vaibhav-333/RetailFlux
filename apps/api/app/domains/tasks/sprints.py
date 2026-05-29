"""Sprint and Milestone service layer."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Milestone, Sprint, SprintTask, Task


# ── Milestones ─────────────────────────────────────────────────────────────────


async def list_milestones(
    db: AsyncSession,
    company_id: uuid.UUID,
    *,
    milestone_status: Optional[str] = None,
    page: int = 1,
    size: int = 25,
) -> tuple[list[Milestone], int]:
    q = select(Milestone).where(Milestone.company_id == company_id)
    if milestone_status:
        q = q.where(Milestone.status == milestone_status)
    total: int = await db.scalar(select(func.count()).select_from(q.subquery())) or 0
    items = list(
        (await db.scalars(q.order_by(Milestone.due_at.nullslast()).offset((page - 1) * size).limit(size))).all()
    )
    return items, total


async def create_milestone(
    db: AsyncSession,
    company_id: uuid.UUID,
    actor_id: uuid.UUID,
    name: str,
    description: Optional[str] = None,
    due_at: Optional[datetime] = None,
) -> Milestone:
    m = Milestone(
        company_id=company_id,
        name=name,
        description=description,
        due_at=due_at,
        created_by=actor_id,
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return m


async def get_milestone(
    db: AsyncSession, company_id: uuid.UUID, milestone_id: uuid.UUID
) -> Milestone:
    m = await db.scalar(
        select(Milestone).where(
            Milestone.id == milestone_id,
            Milestone.company_id == company_id,
        )
    )
    if m is None:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return m


async def update_milestone(
    db: AsyncSession,
    company_id: uuid.UUID,
    milestone_id: uuid.UUID,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    due_at: Optional[datetime] = None,
    milestone_status: Optional[str] = None,
) -> Milestone:
    m = await get_milestone(db, company_id, milestone_id)
    if name is not None:
        m.name = name
    if description is not None:
        m.description = description
    if due_at is not None:
        m.due_at = due_at
    if milestone_status is not None:
        m.status = milestone_status
    m.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(m)
    return m


async def delete_milestone(
    db: AsyncSession, company_id: uuid.UUID, milestone_id: uuid.UUID
) -> None:
    m = await get_milestone(db, company_id, milestone_id)
    await db.delete(m)
    await db.commit()


# ── Sprints ────────────────────────────────────────────────────────────────────


async def list_sprints(
    db: AsyncSession,
    company_id: uuid.UUID,
    *,
    sprint_status: Optional[str] = None,
    page: int = 1,
    size: int = 25,
) -> tuple[list[Sprint], int]:
    q = (
        select(Sprint)
        .options(selectinload(Sprint.sprint_tasks))
        .where(Sprint.company_id == company_id)
    )
    if sprint_status:
        q = q.where(Sprint.status == sprint_status)
    total: int = await db.scalar(select(func.count()).select_from(
        select(Sprint).where(Sprint.company_id == company_id).subquery()
    )) or 0
    items = list(
        (await db.scalars(q.order_by(Sprint.starts_at.desc()).offset((page - 1) * size).limit(size))).all()
    )
    return items, total


async def create_sprint(
    db: AsyncSession,
    company_id: uuid.UUID,
    actor_id: uuid.UUID,
    name: str,
    starts_at: datetime,
    ends_at: datetime,
    *,
    goal: Optional[str] = None,
    capacity_hours: Optional[float] = None,
) -> Sprint:
    if ends_at <= starts_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ends_at must be after starts_at",
        )
    s = Sprint(
        company_id=company_id,
        name=name,
        goal=goal,
        starts_at=starts_at,
        ends_at=ends_at,
        capacity_hours=capacity_hours,
        created_by=actor_id,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s, ["sprint_tasks"])
    return s


async def get_sprint(
    db: AsyncSession, company_id: uuid.UUID, sprint_id: uuid.UUID
) -> Sprint:
    s = await db.scalar(
        select(Sprint)
        .options(selectinload(Sprint.sprint_tasks))
        .where(Sprint.id == sprint_id, Sprint.company_id == company_id)
    )
    if s is None:
        raise HTTPException(status_code=404, detail="Sprint not found")
    return s


async def update_sprint(
    db: AsyncSession,
    company_id: uuid.UUID,
    sprint_id: uuid.UUID,
    *,
    name: Optional[str] = None,
    goal: Optional[str] = None,
    starts_at: Optional[datetime] = None,
    ends_at: Optional[datetime] = None,
    sprint_status: Optional[str] = None,
    capacity_hours: Optional[float] = None,
) -> Sprint:
    s = await get_sprint(db, company_id, sprint_id)
    if name is not None:
        s.name = name
    if goal is not None:
        s.goal = goal
    if starts_at is not None:
        s.starts_at = starts_at
    if ends_at is not None:
        s.ends_at = ends_at
    if sprint_status is not None:
        s.status = sprint_status
    if capacity_hours is not None:
        s.capacity_hours = capacity_hours
    s.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(s, ["sprint_tasks"])
    return s


async def delete_sprint(
    db: AsyncSession, company_id: uuid.UUID, sprint_id: uuid.UUID
) -> None:
    s = await get_sprint(db, company_id, sprint_id)
    await db.delete(s)
    await db.commit()


async def add_task_to_sprint(
    db: AsyncSession,
    company_id: uuid.UUID,
    sprint_id: uuid.UUID,
    task_id: uuid.UUID,
) -> Sprint:
    sprint = await get_sprint(db, company_id, sprint_id)

    # Verify task belongs to same company
    task = await db.scalar(
        select(Task).where(Task.id == task_id, Task.company_id == company_id, Task.deleted_at.is_(None))
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    existing = await db.scalar(
        select(SprintTask).where(SprintTask.sprint_id == sprint_id, SprintTask.task_id == task_id)
    )
    if existing is None:
        db.add(SprintTask(sprint_id=sprint_id, task_id=task_id))
        await db.commit()

    return await get_sprint(db, company_id, sprint_id)


async def remove_task_from_sprint(
    db: AsyncSession,
    company_id: uuid.UUID,
    sprint_id: uuid.UUID,
    task_id: uuid.UUID,
) -> Sprint:
    await get_sprint(db, company_id, sprint_id)
    st = await db.scalar(
        select(SprintTask).where(SprintTask.sprint_id == sprint_id, SprintTask.task_id == task_id)
    )
    if st:
        await db.delete(st)
        await db.commit()
    return await get_sprint(db, company_id, sprint_id)


async def get_sprint_tasks(
    db: AsyncSession,
    company_id: uuid.UUID,
    sprint_id: uuid.UUID,
) -> list[Task]:
    """Return all Task objects assigned to a sprint (ordered by priority)."""
    from sqlalchemy.orm import selectinload as sil  # noqa: PLC0415
    sprint = await get_sprint(db, company_id, sprint_id)
    task_ids = [st.task_id for st in sprint.sprint_tasks]
    if not task_ids:
        return []
    tasks = list(
        (
            await db.scalars(
                select(Task)
                .options(sil(Task.assignees), sil(Task.departments))
                .where(Task.id.in_(task_ids), Task.deleted_at.is_(None))
            )
        ).all()
    )
    return tasks


async def get_department_board(
    db: AsyncSession,
    company_id: uuid.UUID,
    department: str,
    *,
    sprint_id: Optional[uuid.UUID] = None,
    page: int = 1,
    size: int = 100,
) -> tuple[list[Task], int]:
    """Return tasks for a department, optionally filtered to a sprint."""
    from app.models.task import TaskDepartment  # noqa: PLC0415
    from sqlalchemy.orm import selectinload as sil  # noqa: PLC0415

    q = (
        select(Task)
        .options(sil(Task.assignees), sil(Task.departments))
        .join(TaskDepartment, TaskDepartment.task_id == Task.id)
        .where(
            Task.company_id == company_id,
            Task.deleted_at.is_(None),
            TaskDepartment.department == department,
        )
    )
    if sprint_id is not None:
        q = q.join(SprintTask, SprintTask.task_id == Task.id).where(SprintTask.sprint_id == sprint_id)

    total: int = await db.scalar(select(func.count()).select_from(q.subquery())) or 0
    items = list((await db.scalars(q.offset((page - 1) * size).limit(size))).all())
    return items, total
