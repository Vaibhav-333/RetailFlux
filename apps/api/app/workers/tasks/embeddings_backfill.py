"""Celery tasks for embedding backfill and incremental indexing.

Runs as a weekly job (Sunday 05:00 UTC) to embed:
  - AI insight bodies stored in MongoDB
  - Task titles + descriptions from Postgres
  - SKU names + metadata from Postgres sku_master
  - Recent AI insight cache items

Each item is upserted into app.embeddings, so re-runs are safe.
"""
import asyncio

import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="app.workers.tasks.embeddings_backfill.embeddings_backfill_all")
def embeddings_backfill_all() -> dict:
    """Back-fill embeddings for all supported entity types across all companies."""
    return asyncio.run(_async_backfill_all())


async def _async_backfill_all() -> dict:
    from app.core.database import AsyncSessionLocal  # noqa: PLC0415
    from sqlalchemy import text  # noqa: PLC0415

    totals: dict[str, int] = {}

    async with AsyncSessionLocal() as db:
        # Fetch all active company IDs
        result = await db.execute(text("SELECT id FROM app.companies WHERE is_active = true"))
        company_ids = [str(r[0]) for r in result.fetchall()]

    for company_id in company_ids:
        async with AsyncSessionLocal() as db:
            stored = await _backfill_company(db, company_id)
            totals[company_id] = stored

    logger.info("embeddings_backfill_complete", totals=totals)
    return totals


async def _backfill_company(db, company_id: str) -> int:
    from app.core.embeddings import bulk_store_texts  # noqa: PLC0415
    from app.core.mongodb import get_mongo_db  # noqa: PLC0415
    from sqlalchemy import text  # noqa: PLC0415

    items: list[dict] = []

    # ── Tasks ─────────────────────────────────────────────────────────────────
    try:
        result = await db.execute(
            text("""
                SELECT id, title, description, type, status, priority
                FROM app.tasks
                WHERE company_id = :cid AND deleted_at IS NULL
                ORDER BY created_at DESC
                LIMIT 500
            """),
            {"cid": company_id},
        )
        for row in result.fetchall():
            task_id, title, desc, ttype, status, priority = row
            content = f"Task: {title or ''}\nType: {ttype}\nStatus: {status}\nPriority: {priority}\n"
            if desc:
                content += f"Description: {desc[:500]}"
            items.append(
                {
                    "entity_type": "task",
                    "entity_id": str(task_id),
                    "content": content,
                    "metadata": {"status": status, "priority": priority, "type": ttype},
                }
            )
    except Exception as exc:
        logger.warning("backfill_tasks_failed", company_id=company_id, error=str(exc))

    # ── SKU master ────────────────────────────────────────────────────────────
    try:
        result = await db.execute(
            text("""
                SELECT id, sku, name, category, subcategory, abc_class, xyz_class
                FROM app.sku_master
                WHERE company_id = :cid AND status = 'active'
                LIMIT 1000
            """),
            {"cid": company_id},
        )
        for row in result.fetchall():
            sid, sku, name, cat, subcat, abc, xyz = row
            content = (
                f"SKU: {sku} | Name: {name or ''}\n"
                f"Category: {cat or ''} > {subcat or ''}\n"
                f"ABC class: {abc or 'N/A'} | XYZ class: {xyz or 'N/A'}"
            )
            items.append(
                {
                    "entity_type": "sku",
                    "entity_id": str(sku),
                    "content": content,
                    "metadata": {"sku_id": str(sid), "category": cat, "abc": abc},
                }
            )
    except Exception as exc:
        logger.warning("backfill_skus_failed", company_id=company_id, error=str(exc))

    # ── AI Insights from MongoDB ───────────────────────────────────────────────
    try:
        mongo_db = await get_mongo_db()
        cursor = mongo_db.ai_insights.find(
            {"company_id": company_id},
            {"body": 1, "dept": 1, "generated_at": 1},
        ).sort("generated_at", -1).limit(100)

        async for doc in cursor:
            doc_id = str(doc["_id"])
            body = doc.get("body") or doc.get("summary") or ""
            dept = doc.get("dept", "general")
            if not body:
                continue
            items.append(
                {
                    "entity_type": "insight",
                    "entity_id": doc_id,
                    "content": f"AI Insight ({dept}): {body[:600]}",
                    "metadata": {"dept": dept},
                }
            )
    except Exception as exc:
        logger.warning("backfill_insights_failed", company_id=company_id, error=str(exc))

    if not items:
        return 0

    stored = await bulk_store_texts(db, company_id, items)
    logger.info("backfill_company_done", company_id=company_id, stored=stored, total=len(items))
    return stored
