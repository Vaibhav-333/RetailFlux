"""Celery beat task: generate AI task recommendations for all companies."""
from __future__ import annotations

import asyncio
import logging
import uuid

from celery import shared_task
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings

log = logging.getLogger(__name__)

_SYNC_DB_URL = settings.DATABASE_URL.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
)
_engine = create_engine(_SYNC_DB_URL, pool_pre_ping=True)


async def _run_for_company(company_id: str) -> int:
    """Run AI recommendation generation for one company."""
    from app.core.database import AsyncSessionLocal  # noqa: PLC0415
    from app.domains.tasks.recommendation import generate_recommendations  # noqa: PLC0415

    # Use a system-level actor ID (zero UUID) for AI-generated tasks
    actor_id = uuid.UUID(int=0)
    cid = uuid.UUID(company_id)

    async with AsyncSessionLocal() as db:
        try:
            tasks = await generate_recommendations(db, cid, actor_id)
            log.info(
                "AI recommendations: created %d tasks for company %s",
                len(tasks),
                company_id,
            )
            return len(tasks)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "AI recommendations failed for company %s: %s", company_id, exc
            )
            return 0


async def _run_escalation_for_company(company_id: str) -> dict:
    """Run escalation sweep for one company."""
    from app.core.database import AsyncSessionLocal  # noqa: PLC0415
    from app.domains.tasks.escalation_service import run_escalation_sweep  # noqa: PLC0415

    cid = uuid.UUID(company_id)
    async with AsyncSessionLocal() as db:
        try:
            return await run_escalation_sweep(db, cid)
        except Exception as exc:  # noqa: BLE001
            log.warning("Escalation sweep failed for company %s: %s", company_id, exc)
            return {"stuck_escalated": 0, "breach_escalated": 0, "total": 0}


@shared_task(bind=True, name="app.workers.tasks.task_ai_recommendations.task_recommendation_sweep")
def task_recommendation_sweep(self):  # type: ignore[no-untyped-def]
    """Generate AI task recommendations for all active companies."""
    with Session(_engine) as session:
        rows = session.execute(text("SELECT id FROM app.companies")).fetchall()

    company_ids = [str(r[0]) for r in rows]
    log.info("AI recommendation sweep: processing %d companies", len(company_ids))

    total_created = 0
    for cid in company_ids:
        total_created += asyncio.run(_run_for_company(cid))

    log.info("AI recommendation sweep complete: %d total tasks created", total_created)
    return {"companies": len(company_ids), "tasks_created": total_created}


@shared_task(bind=True, name="app.workers.tasks.task_ai_recommendations.task_escalation_sweep")
def task_escalation_sweep(self):  # type: ignore[no-untyped-def]
    """Run escalation sweep across all active companies."""
    with Session(_engine) as session:
        rows = session.execute(text("SELECT id FROM app.companies")).fetchall()

    company_ids = [str(r[0]) for r in rows]
    log.info("Task escalation sweep: processing %d companies", len(company_ids))

    total_stuck = 0
    total_breached = 0
    for cid in company_ids:
        result = asyncio.run(_run_escalation_for_company(cid))
        total_stuck += result.get("stuck_escalated", 0)
        total_breached += result.get("breach_escalated", 0)

    log.info(
        "Escalation sweep complete: stuck=%d breached=%d", total_stuck, total_breached
    )
    return {
        "companies": len(company_ids),
        "stuck_escalated": total_stuck,
        "breach_escalated": total_breached,
    }


async def _run_productivity_rollup(company_id: str) -> dict:
    """Snapshot productivity analytics to MongoDB for one company."""
    from app.core.database import AsyncSessionLocal  # noqa: PLC0415
    from app.domains.tasks.productivity_rollup import snapshot_productivity  # noqa: PLC0415

    cid = uuid.UUID(company_id)
    async with AsyncSessionLocal() as db:
        try:
            return await snapshot_productivity(db, cid)
        except Exception as exc:  # noqa: BLE001
            log.warning("Productivity rollup failed for %s: %s", company_id, exc)
            return {"status": "error", "company_id": company_id}


async def _run_digest_email(company_id: str) -> dict:
    """Send the weekly task digest email for one company."""
    from app.core.database import AsyncSessionLocal  # noqa: PLC0415
    from app.domains.tasks.digest_email import send_task_digest  # noqa: PLC0415

    cid = uuid.UUID(company_id)
    async with AsyncSessionLocal() as db:
        try:
            return await send_task_digest(db, cid)
        except Exception as exc:  # noqa: BLE001
            log.warning("Digest email failed for %s: %s", company_id, exc)
            return {"status": "error", "company_id": company_id}


@shared_task(bind=True, name="app.workers.tasks.task_ai_recommendations.task_productivity_rollup")
def task_productivity_rollup(self):  # type: ignore[no-untyped-def]
    """Daily snapshot of task analytics to MongoDB for all companies."""
    with Session(_engine) as session:
        rows = session.execute(text("SELECT id FROM app.companies")).fetchall()

    company_ids = [str(r[0]) for r in rows]
    log.info("Productivity rollup: processing %d companies", len(company_ids))

    results = []
    for cid in company_ids:
        result = asyncio.run(_run_productivity_rollup(cid))
        results.append(result)

    ok = sum(1 for r in results if r.get("status") == "ok")
    log.info("Productivity rollup complete: %d/%d ok", ok, len(company_ids))
    return {"companies": len(company_ids), "ok": ok}


@shared_task(bind=True, name="app.workers.tasks.task_ai_recommendations.task_weekly_digest")
def task_weekly_digest(self):  # type: ignore[no-untyped-def]
    """Send weekly task analytics digest email to all company managers/admins."""
    with Session(_engine) as session:
        rows = session.execute(text("SELECT id FROM app.companies")).fetchall()

    company_ids = [str(r[0]) for r in rows]
    log.info("Weekly task digest: processing %d companies", len(company_ids))

    total_sent = 0
    for cid in company_ids:
        result = asyncio.run(_run_digest_email(cid))
        total_sent += result.get("emails_sent", 0)

    log.info("Weekly digest complete: %d total emails sent", total_sent)
    return {"companies": len(company_ids), "emails_sent": total_sent}
