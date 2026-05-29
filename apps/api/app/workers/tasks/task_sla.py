"""Celery Beat task: hourly SLA breach sweep for overdue tasks."""
from __future__ import annotations

import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_setup import logger
from app.workers.celery_app import celery_app

_SYNC_DB_URL = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
_engine = create_engine(_SYNC_DB_URL, pool_pre_ping=True)

log = logging.getLogger(__name__)


@celery_app.task(
    name="app.workers.tasks.task_sla.task_sla_sweep",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    soft_time_limit=120,
    time_limit=180,
)
def task_sla_sweep(self) -> dict:  # type: ignore[return]
    """Mark overdue tasks as breached and publish realtime events."""
    try:
        breached_rows: list[dict] = []

        with Session(_engine) as session:
            # Fetch tasks that are overdue but not yet breached
            rows = session.execute(
                text(
                    """
                    UPDATE app.tasks
                       SET breached = true,
                           updated_at = now()
                     WHERE due_at < now()
                       AND status NOT IN ('done', 'cancelled')
                       AND deleted_at IS NULL
                       AND breached = false
                 RETURNING id, company_id, title
                    """
                )
            ).fetchall()
            session.commit()
            breached_rows = [
                {"id": str(r[0]), "company_id": str(r[1]), "title": r[2]}
                for r in rows
            ]

        # Publish per-company realtime events
        if breached_rows:
            from app.core.pubsub import publish_event_sync  # lazy import

            company_groups: dict[str, list[dict]] = {}
            for row in breached_rows:
                company_groups.setdefault(row["company_id"], []).append(row)

            for company_id, tasks in company_groups.items():
                try:
                    publish_event_sync(
                        company_id,
                        "task_sla_breach",
                        {"breached_count": len(tasks), "tasks": tasks},
                    )
                except Exception:
                    log.warning("Failed to publish sla_breach event for company %s", company_id)

        logger.info("task_sla_sweep_done", breached=len(breached_rows))
        return {"breached": len(breached_rows)}

    except Exception as exc:
        logger.error("task_sla_sweep_error", error=str(exc))
        raise self.retry(exc=exc)
