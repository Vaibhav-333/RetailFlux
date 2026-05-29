"""Weekly Celery task: regenerate dynamic pricing suggestions for all active companies."""
from __future__ import annotations

import asyncio
import logging

import structlog
from celery import shared_task

from app.core.mongodb import get_mongo_db
from app.domains.pricing.suggestions_service import refresh_pricing_suggestions

logger = structlog.get_logger()


async def _run_pricing_refresh() -> dict:
    db = get_mongo_db()
    col_companies = db["staging_sales"]

    # Discover all active company IDs from the sales collection
    company_docs = await col_companies.aggregate([
        {"$group": {"_id": "$_company_id"}},
        {"$match": {"_id": {"$ne": None}}},
    ]).to_list(length=1000)

    company_ids = [str(d["_id"]) for d in company_docs if d.get("_id")]

    results = {}
    for company_id in company_ids:
        try:
            count = await refresh_pricing_suggestions(company_id)
            results[company_id] = {"suggestions": count, "status": "ok"}
            logger.info("pricing_weekly.refreshed", company_id=company_id, count=count)
        except Exception as exc:
            results[company_id] = {"status": "error", "error": str(exc)}
            logger.error("pricing_weekly.error", company_id=company_id, error=str(exc))

    return results


@shared_task(name="app.workers.tasks.pricing_weekly.pricing_suggestions_refresh")
def pricing_suggestions_refresh() -> dict:
    """Celery entry point — runs the async refresh synchronously."""
    return asyncio.get_event_loop().run_until_complete(_run_pricing_refresh())
