"""AI explanation service for inventory recommendations — cached in Redis."""
from __future__ import annotations

import json
from typing import Any, Optional

import structlog

from app.core.cache import get_json, set_json
from app.core.gemini import generate_text
from app.schemas.inventory import ExplanationOut

logger = structlog.get_logger()

# Cache for 2 hours — explanations don't need real-time refresh
_EXPLAIN_TTL = 7200
_EXPLAIN_VERSION = 1


def _explain_cache_key(recommendation_id: str) -> str:
    return f"rf:cache:inv_explain:{recommendation_id}:v{_EXPLAIN_VERSION}"


_REORDER_TEMPLATE = """You are a retail inventory analyst. Explain this reorder recommendation in 3-5 sentences for a procurement manager.
Include: why this SKU needs reordering, the EOQ calculation rationale, and what happens if delayed.
Be specific and actionable.

SKU: {sku}
Context:
{context}

Format your response as JSON:
{{
  "rationale": "...",
  "confidence": "high|medium|low",
  "key_factors": ["factor1", "factor2", "factor3"],
  "alternatives": ["alt1", "alt2"]
}}"""


async def explain_reorder_recommendation(
    sku: str,
    context: dict[str, Any],
    recommendation_id: Optional[str] = None,
) -> ExplanationOut:
    """Generate a natural-language explanation for a reorder recommendation."""
    rec_id = recommendation_id or sku
    cache_key = _explain_cache_key(rec_id)

    hit = await get_json(cache_key)
    if hit:
        return ExplanationOut(**hit, cached=True)

    context_str = json.dumps(context, indent=2, default=str)[:2000]
    prompt = _REORDER_TEMPLATE.format(sku=sku, context=context_str)

    try:
        raw_text, provider = await generate_text(prompt)
        raw_text = raw_text.strip()

        # Try to parse as JSON
        if "{" in raw_text:
            start = raw_text.index("{")
            end = raw_text.rindex("}") + 1
            parsed = json.loads(raw_text[start:end])
            rationale = parsed.get("rationale", raw_text)
            confidence = parsed.get("confidence", "medium")
            key_factors = parsed.get("key_factors", [])
            alternatives = parsed.get("alternatives", [])
        else:
            rationale = raw_text
            confidence = "medium"
            key_factors = []
            alternatives = []

    except Exception as exc:
        logger.warning("inventory_explain_failed", sku=sku, error=str(exc))
        rationale = (
            f"Reorder recommended for {sku} based on current stock levels falling below "
            f"the computed reorder point. The EOQ formula optimises order quantity to "
            f"balance ordering and holding costs."
        )
        confidence = "low"
        key_factors = ["Stock below reorder point", "EOQ calculation", "Lead time risk"]
        alternatives = ["Partial order", "Emergency rush order from alternate supplier"]

    result_data = {
        "recommendation_id": rec_id,
        "rationale": rationale,
        "confidence": confidence,
        "key_factors": key_factors[:5],
        "alternatives": alternatives[:3],
    }

    # Cache in Redis (never commit to DB — keep simple)
    await set_json(cache_key, result_data, _EXPLAIN_TTL)
    logger.info("inventory_explain_generated", sku=sku, rec_id=rec_id)

    return ExplanationOut(**result_data, cached=False)
