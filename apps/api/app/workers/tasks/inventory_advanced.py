"""Advanced inventory Celery tasks: reorder refresh, anomaly scan, scoring, seasonality."""
import asyncio
import structlog
from celery import shared_task

logger = structlog.get_logger()


async def _sweep_advanced():
    """Run all advanced inventory computations for all active companies."""
    from app.core.database import AsyncSessionLocal  # noqa: PLC0415
    from app.models.user import User  # noqa: PLC0415
    from sqlalchemy import select, distinct  # noqa: PLC0415

    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(distinct(User.company_id)).where(User.is_active.is_(True))
        )
        company_ids = [str(r[0]) for r in rows.fetchall()]

    for company_id in company_ids:
        try:
            await _compute_company(company_id)
        except Exception as exc:
            logger.warning("inv_advanced_company_failed", company_id=company_id, error=str(exc))


async def _compute_company(company_id: str):
    from app.domains.inventory.reorder_service import get_reorder_queue  # noqa: PLC0415
    from app.domains.inventory.scoring_service import get_health_scores  # noqa: PLC0415
    from app.domains.inventory.anomaly_service import get_inventory_anomalies  # noqa: PLC0415
    from app.domains.inventory.replenishment_service import get_replenishment_suggestions, get_heatmap  # noqa: PLC0415
    from app.core.cache import inventory_key, delete_pattern  # noqa: PLC0415

    # Invalidate stale caches so services recompute fresh
    for name in ["reorder-queue", "understock", "overstock", "health-scores", "anomalies", "replenishment", "heatmap"]:
        await delete_pattern(inventory_key(name, company_id))

    # Warm in parallel
    results = await asyncio.gather(
        get_reorder_queue(company_id),
        get_health_scores(company_id),
        get_inventory_anomalies(company_id),
        get_replenishment_suggestions(company_id),
        get_heatmap(company_id),
        return_exceptions=True,
    )

    errors = [r for r in results if isinstance(r, Exception)]
    if errors:
        logger.warning("inv_advanced_partial_failures", company_id=company_id, errors=len(errors))
    else:
        logger.info("inv_advanced_computed", company_id=company_id)


@shared_task(name="app.workers.tasks.inventory_advanced.inventory_reorder_refresh")
def inventory_reorder_refresh():
    """Hourly: refresh reorder queue + replenishment suggestions."""
    asyncio.run(_sweep_reorder())


async def _sweep_reorder():
    from app.core.database import AsyncSessionLocal  # noqa: PLC0415
    from app.models.user import User  # noqa: PLC0415
    from sqlalchemy import select, distinct  # noqa: PLC0415

    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(distinct(User.company_id)).where(User.is_active.is_(True))
        )
        company_ids = [str(r[0]) for r in rows.fetchall()]

    for company_id in company_ids:
        try:
            from app.domains.inventory.reorder_service import get_reorder_queue  # noqa: PLC0415
            from app.domains.inventory.replenishment_service import get_replenishment_suggestions  # noqa: PLC0415
            from app.core.cache import inventory_key, delete_pattern  # noqa: PLC0415

            await delete_pattern(inventory_key("reorder-queue", company_id))
            await delete_pattern(inventory_key("replenishment", company_id))
            await asyncio.gather(
                get_reorder_queue(company_id),
                get_replenishment_suggestions(company_id),
                return_exceptions=True,
            )
        except Exception as exc:
            logger.warning("reorder_refresh_failed", company_id=company_id, error=str(exc))


@shared_task(name="app.workers.tasks.inventory_advanced.inventory_anomaly_scan")
def inventory_anomaly_scan():
    """Every 6 hours: anomaly detection sweep."""
    asyncio.run(_sweep_anomalies())


async def _sweep_anomalies():
    from app.core.database import AsyncSessionLocal  # noqa: PLC0415
    from app.models.user import User  # noqa: PLC0415
    from sqlalchemy import select, distinct  # noqa: PLC0415

    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(distinct(User.company_id)).where(User.is_active.is_(True))
        )
        company_ids = [str(r[0]) for r in rows.fetchall()]

    for company_id in company_ids:
        try:
            from app.domains.inventory.anomaly_service import get_inventory_anomalies  # noqa: PLC0415
            from app.core.cache import inventory_key, delete_pattern  # noqa: PLC0415

            await delete_pattern(inventory_key("anomalies", company_id))
            anomalies = await get_inventory_anomalies(company_id)
            if anomalies.total > 0:
                logger.info("inv_anomalies_found", company_id=company_id, count=anomalies.total)
        except Exception as exc:
            logger.warning("anomaly_scan_failed", company_id=company_id, error=str(exc))


@shared_task(name="app.workers.tasks.inventory_advanced.inventory_health_score_refresh")
def inventory_health_score_refresh():
    """Nightly: refresh health scores for all companies."""
    asyncio.run(_sweep_health_scores())


async def _sweep_health_scores():
    from app.core.database import AsyncSessionLocal  # noqa: PLC0415
    from app.models.user import User  # noqa: PLC0415
    from sqlalchemy import select, distinct  # noqa: PLC0415

    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(distinct(User.company_id)).where(User.is_active.is_(True))
        )
        company_ids = [str(r[0]) for r in rows.fetchall()]

    for company_id in company_ids:
        try:
            from app.domains.inventory.scoring_service import get_health_scores  # noqa: PLC0415
            from app.core.cache import inventory_key, delete_pattern  # noqa: PLC0415

            await delete_pattern(inventory_key("health-scores", company_id))
            await get_health_scores(company_id)
        except Exception as exc:
            logger.warning("health_score_refresh_failed", company_id=company_id, error=str(exc))
