"""Celery signals — auto-track every task execution into MongoDB celery_metrics."""
import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

import structlog
from celery.signals import task_failure, task_postrun, task_prerun

logger = structlog.get_logger()

# task_id → perf_counter start time
_start_times: Dict[str, float] = {}
_ttl_ensured = False


async def _ensure_ttl() -> None:
    global _ttl_ensured
    if _ttl_ensured:
        return
    try:
        from app.core.mongodb import get_mongo_db  # noqa: PLC0415
        col = get_mongo_db()["celery_metrics"]
        await col.create_index(
            "timestamp",
            expireAfterSeconds=30 * 24 * 3600,  # 30 days
            background=True,
        )
        _ttl_ensured = True
    except Exception as exc:
        logger.warning("celery_metrics_ttl_failed", error=str(exc))


async def _record(
    task_name: str,
    task_id: str,
    status: str,
    duration_ms: float,
    error: Optional[str],
) -> None:
    try:
        await _ensure_ttl()
        from app.core.mongodb import get_mongo_db  # noqa: PLC0415
        col = get_mongo_db()["celery_metrics"]
        await col.insert_one({
            "timestamp": datetime.now(timezone.utc),
            "task_name": task_name.split(".")[-1],   # short name only
            "task_id": task_id,
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "error": error,
        })
    except Exception as exc:
        logger.warning("celery_metrics_record_failed", error=str(exc))


@task_prerun.connect
def on_task_prerun(task_id: str = "", **kwargs) -> None:  # type: ignore[misc]
    _start_times[task_id] = time.perf_counter()


@task_postrun.connect
def on_task_postrun(task_id: str = "", task=None, state: str = "UNKNOWN", **kwargs) -> None:  # type: ignore[misc]
    start = _start_times.pop(task_id, time.perf_counter())
    duration_ms = (time.perf_counter() - start) * 1000
    task_name = task.name if task else "unknown"
    asyncio.run(_record(task_name, task_id, state, duration_ms, None))


@task_failure.connect
def on_task_failure(task_id: str = "", exception: Optional[Exception] = None, task=None, **kwargs) -> None:  # type: ignore[misc]
    _start_times.pop(task_id, None)
    task_name = task.name if task else "unknown"
    asyncio.run(_record(task_name, task_id, "FAILURE", 0.0, str(exception) if exception else None))
