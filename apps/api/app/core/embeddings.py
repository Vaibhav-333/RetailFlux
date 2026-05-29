"""Embedding adapter + pgvector storage/retrieval for the Copilot RAG pipeline.

Supports Gemini text-embedding-004 (768 dims) with graceful fallback to zero-vectors
when no API key is configured (so the rest of the app keeps running).

pgvector is queried via raw asyncpg SQL — no extra Python package needed; the
`::vector` cast handles type coercion server-side.
"""
import asyncio
import json
import uuid
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = structlog.get_logger()

# Set to True once the startup check confirms pgvector is installed.
# When False, store_embedding uses JSONB fallback and search_similar returns [].
# Initialised to None so callers can distinguish "not yet checked" from False.
PGVECTOR_AVAILABLE: bool | None = None


async def init_pgvector_flag(db: AsyncSession) -> bool:
    """Check pgvector availability and cache the result in PGVECTOR_AVAILABLE.

    Call once from app startup (lifespan) after the DB engine is ready.
    """
    global PGVECTOR_AVAILABLE  # noqa: PLW0603
    from app.core.database import check_pgvector_available  # noqa: PLC0415

    PGVECTOR_AVAILABLE = await check_pgvector_available(db)
    logger.info("pgvector_flag_set", available=PGVECTOR_AVAILABLE)
    return PGVECTOR_AVAILABLE


# ── Vector helpers ────────────────────────────────────────────────────────────


def _vec_to_pg(vec: list[float]) -> str:
    """Convert a Python float list to pgvector bracket notation: [0.1,0.2,...]"""
    return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"


def _zero_vec() -> list[float]:
    return [0.0] * settings.COPILOT_EMBED_DIM


# ── Embedding generation ──────────────────────────────────────────────────────


async def embed_text(text_input: str) -> list[float]:
    """Return an embedding for *text_input* using Gemini text-embedding-004.

    Falls back to a zero-vector on any error so callers can proceed without embedding.
    """
    if not settings.GEMINI_API_KEY:
        return _zero_vec()

    try:
        return await asyncio.to_thread(_sync_embed, text_input)
    except Exception as exc:
        logger.warning("embed_text_failed", error=str(exc))
        return _zero_vec()


def _sync_embed(text_input: str) -> list[float]:
    import google.generativeai as genai  # noqa: PLC0415

    genai.configure(api_key=settings.GEMINI_API_KEY)
    result = genai.embed_content(
        model=settings.COPILOT_EMBED_MODEL,
        content=text_input[:8192],  # model limit
    )
    return result["embedding"]


# ── Storage ───────────────────────────────────────────────────────────────────


async def store_embedding(
    db: AsyncSession,
    *,
    company_id: str,
    entity_type: str,
    entity_id: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Upsert an embedding row.  Generates the vector via Gemini if possible."""
    vec = await embed_text(content)
    vec_str = _vec_to_pg(vec)
    meta_json = json.dumps(metadata or {})

    try:
        await db.execute(
            text("""
                INSERT INTO app.embeddings
                    (company_id, entity_type, entity_id, content, embedding, metadata)
                VALUES
                    (:cid, :etype, :eid, :content, :vec::vector, :meta::jsonb)
                ON CONFLICT (company_id, entity_type, entity_id)
                DO UPDATE SET
                    content   = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata  = EXCLUDED.metadata,
                    updated_at = NOW()
            """),
            {
                "cid": company_id,
                "etype": entity_type,
                "eid": entity_id,
                "content": content[:4000],
                "vec": vec_str,
                "meta": meta_json,
            },
        )
        await db.commit()
    except Exception as exc:
        logger.warning("store_embedding_failed", error=str(exc))
        await db.rollback()


# ── Retrieval ─────────────────────────────────────────────────────────────────


async def search_similar(
    db: AsyncSession,
    *,
    query_text: str,
    company_id: str,
    entity_types: list[str] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Find the *limit* most relevant embeddings for *query_text* via cosine similarity.

    Returns a list of dicts: {entity_type, entity_id, content, metadata, distance}.
    Returns an empty list on any error (e.g. pgvector not enabled).
    """
    query_vec = await embed_text(query_text)
    if all(v == 0.0 for v in query_vec):
        return []

    vec_str = _vec_to_pg(query_vec)

    type_filter = ""
    params: dict[str, Any] = {
        "cid": company_id,
        "vec": vec_str,
        "lim": limit,
    }
    if entity_types:
        type_filter = "AND entity_type = ANY(:etypes)"
        params["etypes"] = entity_types

    try:
        result = await db.execute(
            text(f"""
                SELECT entity_type, entity_id, content, metadata,
                       embedding <=> :vec::vector AS distance
                FROM app.embeddings
                WHERE company_id = :cid {type_filter}
                ORDER BY distance
                LIMIT :lim
            """),  # noqa: S608
            params,
        )
        rows = result.fetchall()
        return [
            {
                "entity_type": r[0],
                "entity_id": r[1],
                "content": r[2],
                "metadata": r[3] or {},
                "distance": float(r[4]),
            }
            for r in rows
        ]
    except Exception as exc:
        logger.warning("search_similar_failed", error=str(exc))
        return []


# ── Batch helpers (used by backfill Celery task) ──────────────────────────────


async def bulk_store_texts(
    db: AsyncSession,
    company_id: str,
    items: list[dict[str, Any]],
) -> int:
    """Bulk upsert items, each with {entity_type, entity_id, content, metadata}.

    Returns the number of successfully stored rows.
    """
    stored = 0
    for item in items:
        try:
            await store_embedding(
                db,
                company_id=company_id,
                entity_type=item["entity_type"],
                entity_id=str(item["entity_id"]),
                content=item["content"],
                metadata=item.get("metadata"),
            )
            stored += 1
        except Exception as exc:
            logger.warning("bulk_store_item_failed", entity_id=item.get("entity_id"), error=str(exc))
    return stored
