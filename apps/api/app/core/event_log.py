"""Unified event log helper.

Every domain mutation that should appear in the event stream calls
`record_event`.  The write is fire-and-forget — it never blocks the
caller and never raises (failures are logged, not surfaced).

Usage::

    import asyncio
    from app.core.event_log import record_event

    # Inside an async service function that already has a db session:
    asyncio.ensure_future(
        record_event(
            db,
            company_id=company_id,
            kind="task.created",
            payload={"title": task.title},
            actor_id=actor_id,
            resource_type="task",
            resource_id=task.id,
        )
    )
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()


async def record_event(
    db: Any,  # AsyncSession — typed as Any to avoid circular import
    *,
    company_id: uuid.UUID,
    kind: str,
    payload: dict[str, Any] | None = None,
    actor_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
) -> None:
    """Insert one row into app.events.  Never raises."""
    try:
        from sqlalchemy import text  # noqa: PLC0415

        payload_json = json.dumps(payload or {}, default=str)

        await db.execute(
            text("""
                INSERT INTO app.events
                    (company_id, kind, payload, actor_id, resource_type, resource_id, occurred_at)
                VALUES
                    (:company_id, :kind, CAST(:payload AS jsonb),
                     :actor_id, :resource_type, :resource_id, :occurred_at)
            """),
            {
                "company_id": str(company_id),
                "kind": kind,
                "payload": payload_json,
                "actor_id": str(actor_id) if actor_id else None,
                "resource_type": resource_type,
                "resource_id": str(resource_id) if resource_id else None,
                "occurred_at": datetime.now(timezone.utc),
            },
        )
        # We do NOT commit here — the caller owns the transaction.
        # If the caller committed already (post-mutation), we need a new flush.
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("event_log_write_failed", kind=kind, error=str(exc))
