"""Celery Beat task: nightly demand forecast refresh for all companies."""
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
    name="app.workers.tasks.forecast_tasks.refresh_nightly_forecasts",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=480,
    time_limit=540,
)
def refresh_nightly_forecasts(self) -> dict:  # type: ignore[return]
    """Refresh Prophet demand forecasts for all active companies. Scheduled nightly at 03:00 UTC."""
    try:
        with Session(_engine) as session:
            rows = session.execute(
                text("SELECT id FROM app.companies ORDER BY created_at")
            ).fetchall()
            company_ids = [str(row[0]) for row in rows]

        logger.info("nightly_forecasts_start", company_count=len(company_ids))
        results: dict[str, dict] = {}

        for company_id in company_ids:
            try:
                from app.domains.forecasting.top_skus_forecast import get_top_skus_forecast  # noqa: PLC0415

                forecast = asyncio.run(get_top_skus_forecast(uuid.UUID(company_id), n=5))
                results[company_id] = {
                    "status": "ok",
                    "skus_forecasted": len(forecast.forecasts),
                }
            except Exception as exc:  # noqa: BLE001
                results[company_id] = {"status": "error", "error": str(exc)}
                logger.warning("nightly_forecasts_company_error", company_id=company_id, error=str(exc))

        logger.info("nightly_forecasts_done", results=results)
        return {"companies_processed": len(company_ids), "results": results}

    except Exception as exc:
        logger.error("nightly_forecasts_fatal", error=str(exc))
        raise self.retry(exc=exc)
