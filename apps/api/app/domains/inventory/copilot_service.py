"""Inventory-scoped AI copilot — answers NL questions about stock, reorders, and health."""
from __future__ import annotations

import json

import structlog

from app.core.gemini import generate_text
from app.schemas.inventory import CopilotAskIn, CopilotAskOut

logger = structlog.get_logger()

_SYSTEM_PROMPT = """You are an expert retail inventory analyst with access to the following inventory context.
Answer concisely and factually. Use specific numbers from the context when available.
If the context doesn't contain enough information, say so honestly.
Format: respond in 2-5 sentences unless a list or table is specifically useful."""


async def inventory_copilot_ask(
    question: str,
    company_id: str,
    context: dict | None = None,
) -> CopilotAskOut:
    """Answer an inventory-related question with optional context."""
    ctx_str = json.dumps(context or {}, indent=2, default=str)[:3000]

    prompt = f"""{_SYSTEM_PROMPT}

Company ID: {company_id}
Inventory Context:
{ctx_str}

Question: {question}

Answer:"""

    try:
        answer, provider = await generate_text(prompt)
        answer = answer.strip()
        context_used = list(context.keys()) if context else []
    except Exception as exc:
        logger.warning("inventory_copilot_failed", error=str(exc))
        answer = "Unable to answer at this time. Please ensure API keys are configured and try again."
        provider = "fallback"
        context_used = []

    return CopilotAskOut(
        answer=answer,
        context_used=context_used,
        provider=provider,
    )
