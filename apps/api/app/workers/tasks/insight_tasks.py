"""Celery Beat task: nightly AI insights regeneration for all companies."""
import asyncio
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_setup import logger
from app.workers.celery_app import celery_app

_SYNC_DB_URL = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
_engine = create_engine(_SYNC_DB_URL, pool_pre_ping=True)


@celery_app.task(
    name="app.workers.tasks.insight_tasks.generate_nightly_insights",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=300,
    time_limit=360,
)
def generate_nightly_insights(self) -> dict:  # type: ignore[return]
    """Regenerate AI insights for all active companies. Scheduled nightly at 02:00 UTC."""
    try:
        with Session(_engine) as session:
            rows = session.execute(
                text("SELECT id FROM app.companies ORDER BY created_at")
            ).fetchall()
            company_ids = [str(row[0]) for row in rows]

        logger.info("nightly_insights_start", company_count=len(company_ids))
        results: dict[str, dict] = {}

        for company_id in company_ids:
            try:
                # Lazy import avoids circular deps at module load time
                from app.domains.insights.insight_service import generate_insights  # noqa: PLC0415

                insight = asyncio.run(generate_insights(uuid.UUID(company_id)))
                results[company_id] = {"status": "ok", "provider": insight.generated_by}
            except Exception as exc:  # noqa: BLE001
                results[company_id] = {"status": "error", "error": str(exc)}
                logger.warning("nightly_insights_company_error", company_id=company_id, error=str(exc))

        logger.info("nightly_insights_done", results=results)
        return {"companies_processed": len(company_ids), "results": results}

    except Exception as exc:
        logger.error("nightly_insights_fatal", error=str(exc))
        raise self.retry(exc=exc)
