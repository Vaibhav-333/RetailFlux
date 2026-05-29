import time
from collections.abc import AsyncGenerator

import structlog
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

logger = structlog.get_logger()

# ── Slow query threshold ──────────────────────────────────────────────────────
# Queries taking longer than this are logged at WARNING level.
_SLOW_QUERY_MS = 100


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)


# ── Slow-query event listener ─────────────────────────────────────────────────
# SQLAlchemy fires synchronous events on the underlying sync engine even when
# using the async engine.  We attach to the sync engine via `engine.sync_engine`.

@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
    conn.info.setdefault("query_start_time", []).append(time.monotonic())


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
    start_times: list[float] = conn.info.get("query_start_time", [])
    if not start_times:
        return
    elapsed_ms = (time.monotonic() - start_times.pop()) * 1_000
    if elapsed_ms >= _SLOW_QUERY_MS:
        # Log only the first 200 chars of the statement to avoid giant log lines.
        logger.warning(
            "slow_query_detected",
            duration_ms=round(elapsed_ms, 1),
            statement_preview=statement[:200].replace("\n", " "),
        )

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def set_rls_context(session: AsyncSession, company_id: str, user_id: str) -> None:
    """Set RLS session variables so Postgres row-level security policies apply."""
    await session.execute(text("SET LOCAL app.current_company_id = :cid"), {"cid": company_id})
    await session.execute(text("SET LOCAL app.current_user_id = :uid"), {"uid": user_id})


async def check_pgvector_available(session: AsyncSession) -> bool:
    """Return True if pgvector extension is installed in this Postgres instance.

    Called once at startup; result cached in app.core.embeddings.PGVECTOR_AVAILABLE.
    Copilot RAG falls back to keyword search when False — no crash.
    """
    try:
        result = await session.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        )
        available = result.scalar_one_or_none() is not None
        if not available:
            logger.warning(
                "pgvector_not_available",
                hint="Run scripts/setup_prod_db.sql in Neon console to enable it",
            )
        return available
    except Exception as exc:
        logger.warning("pgvector_check_failed", error=str(exc))
        return False
