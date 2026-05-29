from pydantic import BaseModel


class EndpointStat(BaseModel):
    endpoint: str
    method: str
    request_count: int
    avg_duration_ms: float
    error_rate: float


class HourlyBucket(BaseModel):
    hour: str
    requests: int
    errors: int


class ObservabilityDashboardOut(BaseModel):
    total_requests_24h: int
    error_count_24h: int
    error_rate_24h: float
    avg_duration_ms_24h: float
    p95_duration_ms_24h: float
    hourly_volume: list[HourlyBucket]
    top_endpoints: list[EndpointStat]


# ── Celery task monitoring ──────────────────────────────────────────────────────
class CeleryTaskStat(BaseModel):
    task_name: str
    total: int
    success: int
    failure: int
    success_rate: float
    avg_duration_ms: float


class RecentFailure(BaseModel):
    task_name: str
    error: str | None
    timestamp: str


class CeleryStatsOut(BaseModel):
    total_tasks_24h: int
    success_count_24h: int
    failure_count_24h: int
    success_rate_24h: float
    avg_duration_ms_24h: float
    by_task: list[CeleryTaskStat]
    recent_failures: list[RecentFailure]


# ── AI usage ───────────────────────────────────────────────────────────────────
class AiUsageSummaryOut(BaseModel):
    total_calls_24h: int
    total_tokens_in_24h: int
    total_tokens_out_24h: int
    total_tokens_24h: int
    total_cost_usd_24h: float
    cache_hit_rate_24h: float
    avg_latency_ms_24h: float
    calls_by_provider: dict[str, int]
