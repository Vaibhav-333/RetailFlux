"""Fire-and-forget AI usage tracker.

After every Gemini / Groq call, callers can schedule this coroutine via
``asyncio.ensure_future`` so it never blocks the response path.

The write uses its own short-lived DB session (same pattern as
``metrics_middleware.py`` uses for MongoDB) so the caller does not need
to pass a session.

Cost estimates (rough, for informational display only — actual billing
depends on your plan):
  Gemini 2.5 Flash Lite: $0.000075 / 1K input tokens, $0.0003 / 1K output
  Groq Llama 3.1 8B:     effectively $0 on free tier
  cached:                $0
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()

# ── Cost table (USD per token) ────────────────────────────────────────────────
_COST_IN: dict[str, float] = {
    "gemini": 0.000075 / 1_000,
    "groq":   0.0,
    "cached": 0.0,
    "fallback": 0.0,
}
_COST_OUT: dict[str, float] = {
    "gemini": 0.0003 / 1_000,
    "groq":   0.0,
    "cached": 0.0,
    "fallback": 0.0,
}


def _estimate_cost(provider: str, tokens_in: int, tokens_out: int) -> float:
    in_rate  = _COST_IN.get(provider, 0.0)
    out_rate = _COST_OUT.get(provider, 0.0)
    return round(tokens_in * in_rate + tokens_out * out_rate, 6)


async def record_ai_usage(
    *,
    company_id: uuid.UUID | str | None = None,
    user_id: uuid.UUID | str | None = None,
    provider: str,
    model: str,
    endpoint: str | None = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    latency_ms: int = 0,
    cache_hit: bool = False,
    error: str | None = None,
) -> None:
    """Insert one row into app.ai_usage.  Never raises."""
    try:
        from sqlalchemy import text  # noqa: PLC0415
        from app.core.database import AsyncSessionLocal  # noqa: PLC0415

        cost = _estimate_cost(provider, tokens_in, tokens_out)

        async with AsyncSessionLocal() as db:
            await db.execute(
                text("""
                    INSERT INTO app.ai_usage
                        (company_id, user_id, provider, model, endpoint,
                         tokens_in, tokens_out, latency_ms,
                         cost_estimate_usd, cache_hit, error, occurred_at)
                    VALUES
                        (:company_id, :user_id, :provider, :model, :endpoint,
                         :tokens_in, :tokens_out, :latency_ms,
                         :cost_estimate_usd, :cache_hit, :error, :occurred_at)
                """),
                {
                    "company_id": str(company_id) if company_id else None,
                    "user_id":    str(user_id)    if user_id    else None,
                    "provider":   provider,
                    "model":      model,
                    "endpoint":   endpoint,
                    "tokens_in":  tokens_in,
                    "tokens_out": tokens_out,
                    "latency_ms": latency_ms,
                    "cost_estimate_usd": cost,
                    "cache_hit":  cache_hit,
                    "error":      error,
                    "occurred_at": datetime.now(timezone.utc),
                },
            )
            await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("ai_usage_write_failed", provider=provider, error=str(exc))
