from pydantic import BaseModel


class CacheMetrics(BaseModel):
    hits: int = 0
    misses: int = 0
    stale_hits: int = 0
    hit_rate: float = 0.0
    total_lookups: int = 0


class CacheHealth(BaseModel):
    status: str
    latency_ms: float = -1
    used_memory_human: str = ""
    connected_clients: int = 0
    error: str | None = None


class CacheStatsOut(BaseModel):
    total_keys: int
    by_category: dict[str, int]
    metrics: CacheMetrics = CacheMetrics()
    health: CacheHealth = CacheHealth(status="unknown")


class CacheInvalidateResult(BaseModel):
    deleted: int
    dept: str | None
    warmed: dict[str, bool] | None = None


class CacheWarmResult(BaseModel):
    company_id: str
    warmed: dict[str, bool]
