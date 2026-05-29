"""Daily productivity rollup — snapshot task analytics to MongoDB collections."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


async def snapshot_productivity(
    db: AsyncSession,
    company_id: uuid.UUID,
) -> dict:
    """
    Compute today's analytics and store a snapshot in MongoDB.

    Collections written:
    - ``productivity_daily``   — one doc per (company, date) with team score + dept breakdown
    - ``task_workload_snapshots`` — one doc per (company, date) with per-user workload
    """
    from app.core.mongodb import get_mongo_db  # noqa: PLC0415
    from app.domains.tasks.analytics_service import (  # noqa: PLC0415
        get_department_productivity,
        get_team_score,
        get_workload,
    )

    today = datetime.now(timezone.utc).date().isoformat()
    cid = str(company_id)

    try:
        score = await get_team_score(db, company_id)
        depts = await get_department_productivity(db, company_id)
        workload = await get_workload(db, company_id)
    except Exception as exc:  # noqa: BLE001
        log.warning("Productivity rollup query failed for %s: %s", cid, exc)
        return {"status": "error", "company_id": cid, "error": str(exc)}

    db_mongo = get_mongo_db()

    # ── productivity_daily ────────────────────────────────────────────────────
    productivity_doc = {
        "company_id": cid,
        "date": today,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "team_score": score.model_dump(),
        "department_productivity": [d.model_dump() for d in depts],
    }
    try:
        await db_mongo["productivity_daily"].update_one(
            {"company_id": cid, "date": today},
            {"$set": productivity_doc},
            upsert=True,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("MongoDB productivity_daily write failed for %s: %s", cid, exc)

    # ── task_workload_snapshots ───────────────────────────────────────────────
    workload_doc = {
        "company_id": cid,
        "date": today,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "workload": [
            {
                "user_id": str(w.user_id),
                "open_count": w.open_count,
                "in_progress_count": w.in_progress_count,
                "blocked_count": w.blocked_count,
                "overdue_count": w.overdue_count,
            }
            for w in workload
        ],
    }
    try:
        await db_mongo["task_workload_snapshots"].update_one(
            {"company_id": cid, "date": today},
            {"$set": workload_doc},
            upsert=True,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("MongoDB task_workload_snapshots write failed for %s: %s", cid, exc)

    log.info(
        "Productivity rollup complete — company=%s date=%s depts=%d users=%d",
        cid,
        today,
        len(depts),
        len(workload),
    )
    return {
        "status": "ok",
        "company_id": cid,
        "date": today,
        "departments_snapshotted": len(depts),
        "users_snapshotted": len(workload),
    }


async def get_productivity_history(
    company_id: uuid.UUID,
    days: int = 30,
) -> list[dict]:
    """Retrieve the last `days` productivity snapshots for a company."""
    from app.core.mongodb import get_mongo_db  # noqa: PLC0415

    db_mongo = get_mongo_db()
    cursor = (
        db_mongo["productivity_daily"]
        .find({"company_id": str(company_id)}, {"_id": 0})
        .sort("date", -1)
        .limit(days)
    )
    try:
        return await cursor.to_list(length=days)
    except Exception as exc:  # noqa: BLE001
        log.warning("Productivity history read failed: %s", exc)
        return []
