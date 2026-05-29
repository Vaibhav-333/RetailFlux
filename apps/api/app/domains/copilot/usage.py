"""Daily token-cap tracking per company.

Each call to `check_and_record_usage` atomically increments the usage counter
and returns False (+ a user-facing message) if the daily cap is exceeded.
"""
from __future__ import annotations

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = structlog.get_logger()


async def check_and_record_usage(
    db: AsyncSession,
    *,
    company_id: str,
    estimated_tokens: int = 500,
) -> tuple[bool, str | None]:
    """Check daily token cap and record the usage increment.

    Returns:
        (allowed, error_message)
        - (True, None) → proceed normally.
        - (False, message) → cap exceeded; return message to user.
    """
    try:
        # Upsert today's row and atomically read back the updated total
        result = await db.execute(
            text("""
                INSERT INTO app.copilot_usage_daily
                    (company_id, date, tokens_used, request_count)
                VALUES
                    (:cid, CURRENT_DATE, :tokens, 1)
                ON CONFLICT (company_id, date) DO UPDATE
                    SET tokens_used  = app.copilot_usage_daily.tokens_used + :tokens,
                        request_count = app.copilot_usage_daily.request_count + 1,
                        updated_at    = NOW()
                RETURNING tokens_used
            """),
            {"cid": company_id, "tokens": estimated_tokens},
        )
        row = result.fetchone()
        await db.commit()

        if row and row[0] > settings.COPILOT_DAILY_TOKEN_CAP:
            logger.warning(
                "copilot_daily_cap_exceeded",
                company_id=company_id,
                tokens_used=row[0],
                cap=settings.COPILOT_DAILY_TOKEN_CAP,
            )
            return False, (
                "Your company has reached today's AI Copilot usage limit. "
                f"The daily cap of {settings.COPILOT_DAILY_TOKEN_CAP:,} tokens resets at midnight UTC. "
                "Upgrade your plan or contact support for a higher limit."
            )
    except Exception as exc:
        # Never block the user because of a tracking error
        logger.warning("copilot_usage_check_failed", error=str(exc))
        await db.rollback()

    return True, None


async def get_usage_today(
    db: AsyncSession,
    *,
    company_id: str,
) -> dict:
    """Return today's usage stats for the company."""
    try:
        result = await db.execute(
            text("""
                SELECT tokens_used, request_count
                FROM app.copilot_usage_daily
                WHERE company_id = :cid AND date = CURRENT_DATE
            """),
            {"cid": company_id},
        )
        row = result.fetchone()
        if row:
            return {
                "tokens_used": row[0],
                "request_count": row[1],
                "cap": settings.COPILOT_DAILY_TOKEN_CAP,
                "pct_used": round(row[0] / settings.COPILOT_DAILY_TOKEN_CAP * 100, 1),
            }
    except Exception:
        pass
    return {"tokens_used": 0, "request_count": 0, "cap": settings.COPILOT_DAILY_TOKEN_CAP, "pct_used": 0.0}
