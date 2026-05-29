"""AI-powered task recommendations generated from recent anomalies and alerts."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task, TaskActivity, TaskDepartment

log = logging.getLogger(__name__)


async def _get_context(company_id: uuid.UUID) -> str:
    """Gather recent anomaly + low-stock context from MongoDB analytics."""
    parts: list[str] = []

    try:
        from app.domains.insights.anomaly_service import get_revenue_anomalies  # noqa: PLC0415
        anomalies = await get_revenue_anomalies(str(company_id))
        if anomalies:
            lines = [f"{a.date} z={a.z_score:.1f}" for a in anomalies[:5]]
            parts.append("Revenue anomalies: " + ", ".join(lines))
    except Exception as exc:  # noqa: BLE001
        log.debug("Anomaly context unavailable: %s", exc)

    try:
        from app.domains.analytics.operations_service import get_operations_kpis  # noqa: PLC0415
        ops = await get_operations_kpis(str(company_id))
        if ops.low_stock_skus:
            skus = [s.sku for s in ops.low_stock_skus[:5]]
            parts.append(f"Low-stock SKUs: {', '.join(skus)}")
    except Exception as exc:  # noqa: BLE001
        log.debug("Operations context unavailable: %s", exc)

    return "\n".join(parts)


async def generate_recommendations(
    db: AsyncSession,
    company_id: uuid.UUID,
    actor_id: uuid.UUID,
    context: str | None = None,
) -> list[Task]:
    """Query context, call Gemini, persist AI-recommended tasks."""
    if context is None:
        context = await _get_context(company_id)

    if not context:
        log.info("No recommendation context for company %s — skipping", company_id)
        return []

    prompt = (
        "You are a retail operations AI advisor. Based on these recent alerts for a fashion "
        "retail company, suggest 3 high-priority action tasks the team should act on now.\n\n"
        f"Alerts:\n{context}\n\n"
        "Reply with ONLY a JSON array. Each object must have:\n"
        '- title (string, max 100 chars)\n'
        '- description (string, 1-2 sentences)\n'
        '- priority ("low"|"medium"|"high"|"urgent"|"critical")\n'
        '- task_type ("general"|"anomaly_response"|"reorder"|"approval"|"review"|"incident")\n'
        '- departments (array of: "sales","marketing","operations","finance","procurement")\n\n'
        "JSON only, no markdown:"
    )

    try:
        from app.core.gemini import generate_text  # noqa: PLC0415
        raw, _ = await generate_text(prompt)
        text = raw.strip().replace("```json", "").replace("```", "").strip()
        suggestions = json.loads(text)
        if not isinstance(suggestions, list):
            suggestions = []
    except Exception as exc:  # noqa: BLE001
        log.warning("AI recommendation generation failed: %s", exc)
        return []

    created: list[Task] = []
    for s in suggestions[:5]:
        try:
            task = Task(
                company_id=company_id,
                title=str(s.get("title", "AI Recommended Task"))[:500],
                description=s.get("description"),
                priority=s.get("priority", "medium"),
                task_type=s.get("task_type", "general"),
                source="ai_recommendation",
                created_by=actor_id,
                task_metadata={"ai_generated": True},
            )
            db.add(task)
            await db.flush()

            for dept in s.get("departments", []):
                db.add(TaskDepartment(task_id=task.id, department=str(dept)))

            db.add(TaskActivity(
                task_id=task.id,
                user_id=actor_id,
                kind="ai_suggested",
                new_value="AI-generated recommendation",
            ))
            created.append(task)
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to persist recommendation task: %s", exc)

    if created:
        await db.commit()
        # Reload with relationships
        loaded: list[Task] = []
        for t in created:
            reloaded = await db.scalar(
                select(Task)
                .options(selectinload(Task.departments), selectinload(Task.assignees))
                .where(Task.id == t.id)
            )
            if reloaded:
                loaded.append(reloaded)

        try:
            from app.core.pubsub import publish_event  # noqa: PLC0415
            await publish_event(
                str(company_id),
                {"type": "task_recommendations_created", "count": len(loaded)},
            )
        except Exception:  # noqa: BLE001
            pass

        return loaded

    return []


async def list_recommendations(
    db: AsyncSession, company_id: uuid.UUID, page: int = 1, size: int = 25
) -> tuple[list[Task], int]:
    """Return pending AI-recommended tasks (not yet done or cancelled)."""
    q = (
        select(Task)
        .options(selectinload(Task.departments), selectinload(Task.assignees))
        .where(
            Task.company_id == company_id,
            Task.source == "ai_recommendation",
            Task.deleted_at.is_(None),
            Task.status.notin_(["done", "cancelled"]),
        )
        .order_by(Task.created_at.desc())
    )
    total = await db.scalar(select(func.count()).select_from(q.subquery())) or 0
    items = list((await db.scalars(q.offset((page - 1) * size).limit(size))).all())
    return items, total
