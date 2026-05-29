"""AI explanation service — generates and caches natural-language explanations for metrics,
charts, SKUs, and other resources. Results are cached per (resource, resource_id, version)
in the app.explanations Postgres table to avoid redundant LLM calls."""
import hashlib
import json
from typing import Any

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.gemini import generate_text

logger = structlog.get_logger()

# Current schema version — bump to force regeneration of all explanations
EXPLAIN_VERSION = 1

# Resource-specific prompt templates
_TEMPLATES: dict[str, str] = {
    "metric": (
        "You are a retail analytics expert. Explain the following metric in 2–4 sentences for a "
        "business executive. Focus on what it means, why it matters, and what the current value "
        "implies for the business. Be specific, concise, and avoid jargon.\n\n"
        "Metric: {resource_id}\nContext: {context}\n\nExplanation:"
    ),
    "sku": (
        "You are a retail analyst. Provide a 2–4 sentence explanation of this SKU's performance "
        "for a merchandising manager. Include sell-through health, stock risk, and a brief "
        "recommendation. Be concrete.\n\n"
        "SKU: {resource_id}\nContext: {context}\n\nExplanation:"
    ),
    "chart": (
        "You are a data analyst. Summarize what this chart shows in 2–3 sentences for a "
        "business user. Highlight the most important trend or insight.\n\n"
        "Chart: {resource_id}\nContext: {context}\n\nExplanation:"
    ),
    "anomaly": (
        "You are a retail operations expert. Explain this anomaly in 2–3 sentences. What likely "
        "caused it, what is the business impact, and what action is recommended?\n\n"
        "Anomaly: {resource_id}\nContext: {context}\n\nExplanation:"
    ),
    "default": (
        "You are a retail AI assistant. Explain the following in 2–4 sentences for a business "
        "executive. Be concise and actionable.\n\n"
        "Topic: {resource_id}\nContext: {context}\n\nExplanation:"
    ),
}


def _cache_key(resource: str, resource_id: str, context: dict[str, Any]) -> str:
    """Hash context so different data produces different cache entries."""
    payload = json.dumps(context, sort_keys=True, default=str)
    h = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return f"{resource_id}:{h}"


async def get_explanation(
    db: AsyncSession,
    resource: str,
    resource_id: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return an AI explanation for the given resource, using the DB cache.

    Args:
        db: SQLAlchemy async session.
        resource: Resource type (metric, sku, chart, anomaly, ...).
        resource_id: The specific resource identifier (e.g. "gross_margin", "BLZ-BLK-M").
        context: Optional dict of context data to ground the explanation.

    Returns:
        {"body": str, "resource": str, "resource_id": str, "cached": bool}
    """
    ctx = context or {}
    effective_id = _cache_key(resource, resource_id, ctx)

    # Check cache
    row = await db.execute(
        text(
            "SELECT body FROM app.explanations "
            "WHERE resource = :r AND resource_id = :rid AND version = :v "
            "LIMIT 1"
        ),
        {"r": resource, "rid": effective_id, "v": EXPLAIN_VERSION},
    )
    cached_row = row.fetchone()
    if cached_row:
        logger.debug("explanation_cache_hit", resource=resource, resource_id=resource_id)
        return {
            "body": cached_row[0],
            "resource": resource,
            "resource_id": resource_id,
            "cached": True,
            "version": EXPLAIN_VERSION,
        }

    # Generate via LLM
    template = _TEMPLATES.get(resource, _TEMPLATES["default"])
    context_str = (
        json.dumps(ctx, indent=2, default=str)[:1500]
        if ctx
        else "No additional context available."
    )
    prompt = template.format(resource_id=resource_id, context=context_str)

    try:
        body, provider = await generate_text(prompt)
        body = body.strip()
    except Exception as exc:
        logger.warning("explanation_llm_failed", error=str(exc))
        body = f"Unable to generate explanation for {resource_id} at this time."
        provider = "fallback"

    # Store in cache (ignore conflict — another request may have raced us)
    try:
        await db.execute(
            text(
                "INSERT INTO app.explanations (resource, resource_id, version, body) "
                "VALUES (:r, :rid, :v, :body) "
                "ON CONFLICT (resource, resource_id, version) DO NOTHING"
            ),
            {"r": resource, "rid": effective_id, "v": EXPLAIN_VERSION, "body": body},
        )
        await db.commit()
        logger.info(
            "explanation_generated",
            resource=resource,
            resource_id=resource_id,
            provider=provider,
        )
    except Exception as exc:
        logger.warning("explanation_cache_write_failed", error=str(exc))
        await db.rollback()

    return {
        "body": body,
        "resource": resource,
        "resource_id": resource_id,
        "cached": False,
        "version": EXPLAIN_VERSION,
    }
