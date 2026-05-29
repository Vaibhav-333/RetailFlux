"""Task escalation: auto-escalate breached/stuck high-priority tasks."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task, TaskActivity

log = logging.getLogger(__name__)

# Tasks in these states are eligible for escalation
_ACTIVE_STATUSES = ("todo", "in_progress", "blocked", "review")

# Priority levels that trigger escalation when stuck
_HIGH_PRIORITIES = ("high", "urgent", "critical")


async def escalate_stuck_tasks(
    db: AsyncSession,
    company_id: uuid.UUID,
    *,
    stuck_hours: int = 48,
    dry_run: bool = False,
) -> list[uuid.UUID]:
    """
    Find active tasks not updated within `stuck_hours` and mark them as escalated.

    Returns list of task IDs that were escalated.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=stuck_hours)

    stmt = (
        select(Task)
        .options(selectinload(Task.assignees))
        .where(
            Task.company_id == company_id,
            Task.deleted_at.is_(None),
            Task.status.in_(list(_ACTIVE_STATUSES)),
            Task.priority.in_(list(_HIGH_PRIORITIES)),
            Task.updated_at < cutoff,
        )
        .order_by(Task.updated_at.asc())
        .limit(50)
    )

    tasks = list((await db.scalars(stmt)).all())
    escalated: list[uuid.UUID] = []

    for task in tasks:
        try:
            if not dry_run:
                db.add(
                    TaskActivity(
                        task_id=task.id,
                        user_id=None,
                        kind="escalated",
                        old_value=task.status,
                        new_value="escalated",
                    )
                )
            escalated.append(task.id)
            log.info(
                "Escalating task %s (company=%s, priority=%s, stuck>%dh)",
                task.id,
                company_id,
                task.priority,
                stuck_hours,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to escalate task %s: %s", task.id, exc)

    if escalated and not dry_run:
        await db.commit()

    return escalated


async def escalate_breached_tasks(
    db: AsyncSession,
    company_id: uuid.UUID,
    *,
    dry_run: bool = False,
) -> list[uuid.UUID]:
    """
    Find tasks that have breached their SLA and log escalation activity if not already done.
    """
    stmt = (
        select(Task)
        .where(
            Task.company_id == company_id,
            Task.deleted_at.is_(None),
            Task.status.in_(list(_ACTIVE_STATUSES)),
            Task.breached.is_(True),
        )
        .order_by(Task.due_at.asc())
        .limit(100)
    )

    tasks = list((await db.scalars(stmt)).all())

    # Check which already have a breach escalation entry to avoid duplicates
    if not tasks:
        return []

    task_ids = [t.id for t in tasks]
    existing_stmt = select(TaskActivity.task_id).where(
        TaskActivity.task_id.in_(task_ids),
        TaskActivity.kind == "sla_breached_escalation",
    )
    already_escalated = set((await db.scalars(existing_stmt)).all())

    escalated: list[uuid.UUID] = []
    for task in tasks:
        if task.id in already_escalated:
            continue
        try:
            if not dry_run:
                db.add(
                    TaskActivity(
                        task_id=task.id,
                        user_id=None,
                        kind="sla_breached_escalation",
                        old_value=None,
                        new_value=f"SLA breached — due {task.due_at}",
                    )
                )
            escalated.append(task.id)
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to record breach escalation for task %s: %s", task.id, exc)

    if escalated and not dry_run:
        await db.commit()

    log.info(
        "Breach escalation: %d tasks processed for company %s", len(escalated), company_id
    )
    return escalated


async def run_escalation_sweep(
    db: AsyncSession,
    company_id: uuid.UUID,
) -> dict:
    """Run all escalation checks for a company. Returns summary dict."""
    stuck = await escalate_stuck_tasks(db, company_id)
    breached = await escalate_breached_tasks(db, company_id)

    try:
        from app.core.pubsub import publish_event  # noqa: PLC0415
        if stuck or breached:
            await publish_event(
                str(company_id),
                {
                    "type": "task_escalation_sweep",
                    "stuck_count": len(stuck),
                    "breached_count": len(breached),
                },
            )
    except Exception:  # noqa: BLE001
        pass

    return {
        "stuck_escalated": len(stuck),
        "breach_escalated": len(breached),
        "total": len(stuck) + len(breached),
    }
