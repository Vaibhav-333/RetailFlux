"""Celery Beat task: hourly alert check for all active companies."""
import asyncio
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_setup import logger
from app.core.pubsub import publish_event_sync
from app.workers.celery_app import celery_app

_SYNC_DB_URL = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
_engine = create_engine(_SYNC_DB_URL, pool_pre_ping=True)


@celery_app.task(
    name="app.workers.tasks.alert_tasks.periodic_alert_check",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    soft_time_limit=180,
    time_limit=240,
)
def periodic_alert_check(self) -> dict:  # type: ignore[return]
    """Run check_and_send_alerts for all active companies. Scheduled every hour."""
    try:
        with Session(_engine) as session:
            rows = session.execute(
                text("SELECT id FROM app.companies ORDER BY created_at")
            ).fetchall()
            company_ids = [str(row[0]) for row in rows]

        logger.info("periodic_alert_check_start", company_count=len(company_ids))
        results: dict[str, dict] = {}

        for company_id in company_ids:
            try:
                # Lazy imports avoid circular deps at module load time
                from app.core.database import AsyncSessionLocal  # noqa: PLC0415
                from app.domains.alerts.alert_service import check_and_send_alerts  # noqa: PLC0415

                async def _run(cid: str) -> dict:
                    async with AsyncSessionLocal() as db:
                        return await check_and_send_alerts(uuid.UUID(cid), db)

                result = asyncio.run(_run(company_id))
                results[company_id] = {
                    "anomalies_found": result.anomalies_found,
                    "low_stock_skus_found": result.low_stock_skus_found,
                    "emails_sent": result.emails_sent,
                    "notifications_created": result.notifications_created,
                }

                if result.notifications_created > 0:
                    publish_event_sync(
                        company_id,
                        "alert",
                        {
                            "anomalies_found": result.anomalies_found,
                            "low_stock_skus_found": result.low_stock_skus_found,
                        },
                    )
            except Exception as exc:  # noqa: BLE001
                results[company_id] = {"status": "error", "error": str(exc)}
                logger.warning(
                    "periodic_alert_check_company_error",
                    company_id=company_id,
                    error=str(exc),
                )

        logger.info("periodic_alert_check_done", results=results)
        return {"companies_processed": len(company_ids), "results": results}

    except Exception as exc:
        logger.error("periodic_alert_check_fatal", error=str(exc))
        raise self.retry(exc=exc)
