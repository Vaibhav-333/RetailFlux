"""Nightly inventory recompute: warms Redis caches for all companies."""
from __future__ import annotations

import asyncio
import logging

from celery import shared_task

from app.core.database import AsyncSessionLocal
from app.domains.inventory.abc_xyz_service import get_abc_xyz_matrix
from app.domains.inventory.aging_service import get_aging_buckets
from app.domains.inventory.service import get_inventory_overview
from app.domains.inventory.valuation_service import get_valuation
from app.domains.inventory.velocity_service import get_velocity

logger = logging.getLogger(__name__)


async def _recompute_for_company(company_id: str) -> None:
    try:
        await asyncio.gather(
            get_inventory_overview(company_id),
            get_abc_xyz_matrix(company_id),
            get_aging_buckets(company_id),
            get_valuation(company_id),
            get_velocity(company_id),
        )
        logger.info("inventory_nightly: recomputed company=%s", company_id)
    except Exception as exc:
        logger.warning("inventory_nightly: error company=%s: %s", company_id, exc)


async def _sweep() -> None:
    from sqlalchemy import text

    async with AsyncSessionLocal() as db:
        rows = await db.execute(text("SELECT id FROM app.companies WHERE is_active = true"))
        company_ids = [str(r[0]) for r in rows.fetchall()]

    for cid in company_ids:
        await _recompute_for_company(cid)


@shared_task(name="app.workers.tasks.inventory_nightly.inventory_nightly_recompute")
def inventory_nightly_recompute() -> None:
    asyncio.run(_sweep())
