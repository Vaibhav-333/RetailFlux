"""Task analytics: department productivity, user workload, bottlenecks, team score."""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task, TaskAssignee, TaskDepartment
from app.schemas.task import (
    BottleneckTask,
    DepartmentProductivity,
    TaskAnalyticsDashboard,
    TeamScore,
    UserWorkload,
)


async def get_department_productivity(
    db: AsyncSession, company_id: uuid.UUID
) -> list[DepartmentProductivity]:
    """Count tasks per department grouped by status."""
    stmt = (
        select(
            TaskDepartment.department,
            func.count(Task.id).label("total"),
            func.sum(case((Task.status == "done", 1), else_=0)).label("done"),
            func.sum(case((Task.status == "in_progress", 1), else_=0)).label("in_progress"),
            func.sum(case((Task.status == "blocked", 1), else_=0)).label("blocked"),
        )
        .join(Task, Task.id == TaskDepartment.task_id)
        .where(Task.company_id == company_id, Task.deleted_at.is_(None))
        .group_by(TaskDepartment.department)
        .order_by(func.count(Task.id).desc())
    )
    rows = (await db.execute(stmt)).all()
    return [
        DepartmentProductivity(
            department=row.department,
            total=row.total,
            done=int(row.done or 0),
            in_progress=int(row.in_progress or 0),
            blocked=int(row.blocked or 0),
            completion_rate=round(int(row.done or 0) / row.total, 4) if row.total else 0.0,
        )
        for row in rows
    ]


async def get_workload(
    db: AsyncSession, company_id: uuid.UUID
) -> list[UserWorkload]:
    """Count open tasks per assignee with status breakdown."""
    stmt = (
        select(TaskAssignee.user_id, Task.status, Task.due_at)
        .join(Task, Task.id == TaskAssignee.task_id)
        .where(
            Task.company_id == company_id,
            Task.deleted_at.is_(None),
            Task.status.notin_(["done", "cancelled"]),
        )
    )
    rows = (await db.execute(stmt)).all()

    now = datetime.now(timezone.utc)
    stats: dict[uuid.UUID, dict] = defaultdict(
        lambda: {"open": 0, "in_progress": 0, "blocked": 0, "overdue": 0}
    )
    for user_id, status, due_at in rows:
        stats[user_id]["open"] += 1
        if status == "in_progress":
            stats[user_id]["in_progress"] += 1
        elif status == "blocked":
            stats[user_id]["blocked"] += 1
        if due_at:
            due = due_at if due_at.tzinfo else due_at.replace(tzinfo=timezone.utc)
            if due < now:
                stats[user_id]["overdue"] += 1

    return [
        UserWorkload(
            user_id=uid,
            open_count=s["open"],
            in_progress_count=s["in_progress"],
            blocked_count=s["blocked"],
            overdue_count=s["overdue"],
            total_open=s["open"],
        )
        for uid, s in sorted(stats.items(), key=lambda x: x[1]["open"], reverse=True)
    ]


async def get_bottlenecks(
    db: AsyncSession,
    company_id: uuid.UUID,
    stuck_hours: int = 24,
    limit: int = 20,
) -> list[BottleneckTask]:
    """Return tasks not updated in >= stuck_hours and not in a terminal state."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=stuck_hours)
    stmt = (
        select(Task)
        .options(selectinload(Task.departments))
        .where(
            Task.company_id == company_id,
            Task.deleted_at.is_(None),
            Task.status.notin_(["done", "cancelled"]),
            Task.updated_at < cutoff,
        )
        .order_by(Task.updated_at.asc())
        .limit(limit)
    )
    tasks = list((await db.scalars(stmt)).all())

    now = datetime.now(timezone.utc)
    result: list[BottleneckTask] = []
    for t in tasks:
        ua = t.updated_at if t.updated_at.tzinfo else t.updated_at.replace(tzinfo=timezone.utc)
        delta_days = round((now - ua).total_seconds() / 86400, 1)
        result.append(
            BottleneckTask(
                task_id=t.id,
                title=t.title,
                status=t.status,
                priority=t.priority,
                days_stuck=delta_days,
                departments=[d.department for d in t.departments],
                breached=t.breached,
            )
        )
    return result


async def get_team_score(db: AsyncSession, company_id: uuid.UUID) -> TeamScore:
    """Composite team performance metrics."""
    stmt = select(
        func.count(Task.id).label("total"),
        func.sum(case((Task.status == "done", 1), else_=0)).label("done"),
        func.sum(
            case((Task.status.notin_(["done", "cancelled"]), 1), else_=0)
        ).label("open"),
        func.sum(
            case(
                (
                    (Task.status.notin_(["done", "cancelled"]))
                    & Task.due_at.isnot(None)
                    & (Task.due_at < func.now()),
                    1,
                ),
                else_=0,
            )
        ).label("overdue"),
        func.sum(
            case(
                (
                    (Task.status == "done") & (Task.breached == False),  # noqa: E712
                    1,
                ),
                else_=0,
            )
        ).label("done_on_time"),
    ).where(Task.company_id == company_id, Task.deleted_at.is_(None))

    row = (await db.execute(stmt)).one()
    total = int(row.total or 0)
    done = int(row.done or 0)
    done_on_time = int(row.done_on_time or 0)

    # Average cycle days for completed tasks (created_at → updated_at proxy)
    avg_stmt = select(
        func.avg(
            func.extract("epoch", Task.updated_at - Task.created_at) / 86400.0
        ).label("avg_days")
    ).where(
        Task.company_id == company_id,
        Task.deleted_at.is_(None),
        Task.status == "done",
    )
    avg_row = (await db.execute(avg_stmt)).one()

    return TeamScore(
        total_tasks=total,
        done_tasks=done,
        open_tasks=int(row.open or 0),
        overdue_tasks=int(row.overdue or 0),
        completion_rate=round(done / total, 4) if total else 0.0,
        on_time_rate=round(done_on_time / done, 4) if done else 0.0,
        avg_cycle_days=round(float(avg_row.avg_days or 0), 1),
    )


async def get_analytics_dashboard(
    db: AsyncSession, company_id: uuid.UUID
) -> TaskAnalyticsDashboard:
    """Collect all four analytics metrics sequentially (single shared session)."""
    dept = await get_department_productivity(db, company_id)
    workload = await get_workload(db, company_id)
    bottlenecks = await get_bottlenecks(db, company_id)
    score = await get_team_score(db, company_id)
    return TaskAnalyticsDashboard(
        department_productivity=dept,
        workload=workload,
        bottlenecks=bottlenecks,
        team_score=score,
    )
