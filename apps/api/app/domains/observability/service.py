import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import cache as _cache
from app.core.mongodb import get_mongo_db
from app.schemas.cache import CacheHealth, CacheMetrics, CacheStatsOut
from app.schemas.observability import (
    AiUsageSummaryOut,
    CeleryStatsOut,
    CeleryTaskStat,
    EndpointStat,
    HourlyBucket,
    ObservabilityDashboardOut,
    RecentFailure,
)


def _since_24h() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=24)


async def get_observability_dashboard() -> ObservabilityDashboardOut:
    col = get_mongo_db()["api_metrics"]
    match = {"timestamp": {"$gte": _since_24h()}}

    # ── Summary stats ──────────────────────────────────────────────────────────
    summary_docs = await col.aggregate([
        {"$match": match},
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "errors": {"$sum": {"$cond": ["$is_error", 1, 0]}},
            "avg_duration": {"$avg": "$duration_ms"},
        }},
    ]).to_list(length=1)

    total: int = summary_docs[0]["total"] if summary_docs else 0
    error_count: int = summary_docs[0]["errors"] if summary_docs else 0
    avg_dur = round(float(summary_docs[0]["avg_duration"] or 0), 2) if summary_docs else 0.0
    error_rate = round(error_count / total, 4) if total > 0 else 0.0

    # ── P95 latency (sort + skip approximation) ────────────────────────────────
    p95 = await _compute_p95(col, match, total)

    # ── Hourly volume (last 24h) ───────────────────────────────────────────────
    hourly_docs = await col.aggregate([
        {"$match": match},
        {"$group": {
            "_id": {
                "$dateToString": {
                    "format": "%Y-%m-%dT%H:00:00",
                    "date": "$timestamp",
                    "timezone": "UTC",
                }
            },
            "requests": {"$sum": 1},
            "errors": {"$sum": {"$cond": ["$is_error", 1, 0]}},
        }},
        {"$sort": {"_id": 1}},
    ]).to_list(length=48)
    hourly_volume = [
        HourlyBucket(hour=d["_id"], requests=d["requests"], errors=d["errors"])
        for d in hourly_docs
    ]

    # ── Top endpoints by request count ────────────────────────────────────────
    endpoint_docs = await col.aggregate([
        {"$match": match},
        {"$group": {
            "_id": {"endpoint": "$endpoint", "method": "$method"},
            "request_count": {"$sum": 1},
            "avg_duration_ms": {"$avg": "$duration_ms"},
            "error_count": {"$sum": {"$cond": ["$is_error", 1, 0]}},
        }},
        {"$sort": {"request_count": -1}},
        {"$limit": 15},
    ]).to_list(length=15)
    top_endpoints = [
        EndpointStat(
            endpoint=d["_id"]["endpoint"],
            method=d["_id"]["method"],
            request_count=d["request_count"],
            avg_duration_ms=round(float(d["avg_duration_ms"] or 0), 2),
            error_rate=round(d["error_count"] / d["request_count"], 4) if d["request_count"] > 0 else 0.0,
        )
        for d in endpoint_docs
    ]

    return ObservabilityDashboardOut(
        total_requests_24h=total,
        error_count_24h=error_count,
        error_rate_24h=error_rate,
        avg_duration_ms_24h=avg_dur,
        p95_duration_ms_24h=p95,
        hourly_volume=hourly_volume,
        top_endpoints=top_endpoints,
    )


async def _compute_p95(col, match: dict, total: int) -> float:
    """Approximate P95 by sorting and skipping 95% of results."""
    if total < 1:
        return 0.0
    skip = max(0, int(total * 0.95) - 1)
    docs = (
        await col.find(match, {"duration_ms": 1, "_id": 0})
        .sort("duration_ms", 1)
        .skip(skip)
        .limit(1)
        .to_list(1)
    )
    return round(float(docs[0]["duration_ms"]), 2) if docs else 0.0


async def get_celery_stats() -> CeleryStatsOut:
    """Aggregate Celery task metrics from the last 24 hours."""
    col = get_mongo_db()["celery_metrics"]
    since = _since_24h()
    match = {"timestamp": {"$gte": since}}

    # ── Summary ───────────────────────────────────────────────────────────────
    summary_docs = await col.aggregate([
        {"$match": match},
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "success": {"$sum": {"$cond": [{"$eq": ["$status", "SUCCESS"]}, 1, 0]}},
            "failure": {"$sum": {"$cond": [{"$eq": ["$status", "FAILURE"]}, 1, 0]}},
            "avg_duration": {"$avg": "$duration_ms"},
        }},
    ]).to_list(length=1)

    total: int = summary_docs[0]["total"] if summary_docs else 0
    success: int = summary_docs[0]["success"] if summary_docs else 0
    failure: int = summary_docs[0]["failure"] if summary_docs else 0
    avg_dur: float = round(float(summary_docs[0]["avg_duration"] or 0), 2) if summary_docs else 0.0
    success_rate: float = round(success / total, 4) if total > 0 else 0.0

    # ── Per-task breakdown ────────────────────────────────────────────────────
    by_task_docs = await col.aggregate([
        {"$match": match},
        {"$group": {
            "_id": "$task_name",
            "total": {"$sum": 1},
            "success": {"$sum": {"$cond": [{"$eq": ["$status", "SUCCESS"]}, 1, 0]}},
            "failure": {"$sum": {"$cond": [{"$eq": ["$status", "FAILURE"]}, 1, 0]}},
            "avg_duration": {"$avg": "$duration_ms"},
        }},
        {"$sort": {"total": -1}},
    ]).to_list(length=20)
    by_task = [
        CeleryTaskStat(
            task_name=d["_id"],
            total=d["total"],
            success=d["success"],
            failure=d["failure"],
            success_rate=round(d["success"] / d["total"], 4) if d["total"] > 0 else 0.0,
            avg_duration_ms=round(float(d["avg_duration"] or 0), 2),
        )
        for d in by_task_docs
    ]

    # ── Recent failures (last 10) ─────────────────────────────────────────────
    failure_docs = await col.aggregate([
        {"$match": {**match, "status": "FAILURE"}},
        {"$sort": {"timestamp": -1}},
        {"$limit": 10},
    ]).to_list(length=10)
    recent_failures = [
        RecentFailure(
            task_name=d["task_name"],
            error=d.get("error"),
            timestamp=d["timestamp"].isoformat() if hasattr(d["timestamp"], "isoformat") else str(d["timestamp"]),
        )
        for d in failure_docs
    ]

    return CeleryStatsOut(
        total_tasks_24h=total,
        success_count_24h=success,
        failure_count_24h=failure,
        success_rate_24h=success_rate,
        avg_duration_ms_24h=avg_dur,
        by_task=by_task,
        recent_failures=recent_failures,
    )


async def get_ai_usage_stats(
    db: AsyncSession,
    company_id: uuid.UUID,
) -> AiUsageSummaryOut:
    """Aggregate AI usage from app.ai_usage for the last 24 hours."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    result = await db.execute(
        text("""
            SELECT
                COUNT(*)                                                AS total_calls,
                COALESCE(SUM(tokens_in), 0)                             AS total_tokens_in,
                COALESCE(SUM(tokens_out), 0)                            AS total_tokens_out,
                COALESCE(SUM(tokens_in + tokens_out), 0)                AS total_tokens,
                COALESCE(SUM(cost_estimate_usd), 0)                     AS total_cost,
                CASE WHEN COUNT(*) > 0
                     THEN ROUND(SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::numeric
                          / COUNT(*), 4)
                     ELSE 0 END                                         AS cache_hit_rate,
                COALESCE(AVG(latency_ms), 0)                            AS avg_latency_ms
            FROM app.ai_usage
            WHERE company_id = :company_id
              AND occurred_at >= :since
        """),
        {"company_id": str(company_id), "since": since},
    )
    row = result.fetchone()

    # Provider breakdown
    provider_result = await db.execute(
        text("""
            SELECT provider, COUNT(*) AS cnt
            FROM app.ai_usage
            WHERE company_id = :company_id
              AND occurred_at >= :since
            GROUP BY provider
        """),
        {"company_id": str(company_id), "since": since},
    )
    calls_by_provider = {r.provider: r.cnt for r in provider_result.fetchall()}

    if row is None or row.total_calls == 0:
        return AiUsageSummaryOut(
            total_calls_24h=0,
            total_tokens_in_24h=0,
            total_tokens_out_24h=0,
            total_tokens_24h=0,
            total_cost_usd_24h=0.0,
            cache_hit_rate_24h=0.0,
            avg_latency_ms_24h=0.0,
            calls_by_provider=calls_by_provider,
        )

    return AiUsageSummaryOut(
        total_calls_24h=int(row.total_calls),
        total_tokens_in_24h=int(row.total_tokens_in),
        total_tokens_out_24h=int(row.total_tokens_out),
        total_tokens_24h=int(row.total_tokens),
        total_cost_usd_24h=float(row.total_cost),
        cache_hit_rate_24h=float(row.cache_hit_rate),
        avg_latency_ms_24h=round(float(row.avg_latency_ms), 1),
        calls_by_provider=calls_by_provider,
    )


async def get_cache_stats() -> CacheStatsOut:
    """Return Redis key counts by cache category, hit/miss metrics, and health."""
    data = await _cache.get_stats()
    return CacheStatsOut(
        total_keys=data["total_keys"],
        by_category=data["by_category"],
        metrics=CacheMetrics(**data.get("metrics", {})),
        health=CacheHealth(**data.get("health", {"status": "unknown"})),
    )
