"""Gemini / Groq LLM client with AI usage tracking.

Every call to ``generate_text`` records one row in ``app.ai_usage`` as a
fire-and-forget background task (never blocks the response).

Callers that have company / user context pass it via keyword args:
    text, provider = await generate_text(
        prompt,
        _company_id=current_user.company_id,
        _user_id=current_user.id,
        _endpoint="/api/v1/copilot/stream",
    )

Callers without context (Celery tasks, background services) omit the
kwargs — usage is still recorded, just without company/user attribution.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from app.core.config import settings


async def generate_text(
    prompt: str,
    *,
    _company_id: uuid.UUID | str | None = None,
    _user_id: uuid.UUID | str | None = None,
    _endpoint: str | None = None,
) -> tuple[str, str]:
    """Call Gemini → Groq → static fallback. Returns (text, provider).

    Keyword args prefixed with ``_`` carry tracking context and are never
    forwarded to the LLM.
    """
    if settings.GEMINI_API_KEY:
        try:
            t0 = time.monotonic()
            text, tokens_in, tokens_out = await _call_gemini(prompt)
            latency_ms = int((time.monotonic() - t0) * 1_000)
            _fire_usage(
                company_id=_company_id,
                user_id=_user_id,
                provider="gemini",
                model=settings.GEMINI_MODEL,
                endpoint=_endpoint,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
            )
            return text, "gemini"
        except Exception:
            pass

    if settings.GROQ_API_KEY:
        try:
            t0 = time.monotonic()
            text, tokens_in, tokens_out = await _call_groq(prompt)
            latency_ms = int((time.monotonic() - t0) * 1_000)
            _fire_usage(
                company_id=_company_id,
                user_id=_user_id,
                provider="groq",
                model=settings.GROQ_MODEL,
                endpoint=_endpoint,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
            )
            return text, "groq"
        except Exception:
            pass

    _fire_usage(
        company_id=_company_id,
        user_id=_user_id,
        provider="fallback",
        model="static",
        endpoint=_endpoint,
        error="no_provider_configured",
    )
    return _static_fallback(), "fallback"


# ── Internal call helpers ──────────────────────────────────────────────────────


async def _call_gemini(prompt: str) -> tuple[str, int, int]:
    """Returns (text, tokens_in, tokens_out)."""
    import google.generativeai as genai  # noqa: PLC0415
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL)
    response = await asyncio.to_thread(model.generate_content, prompt)
    text = response.text

    # Extract token counts from usage metadata when available
    usage = getattr(response, "usage_metadata", None)
    tokens_in  = getattr(usage, "prompt_token_count",     0) or 0
    tokens_out = getattr(usage, "candidates_token_count", 0) or 0

    # Rough fallback: ~4 chars per token
    if tokens_in == 0:
        tokens_in  = max(1, len(prompt) // 4)
    if tokens_out == 0:
        tokens_out = max(1, len(text) // 4)

    return text, tokens_in, tokens_out


async def _call_groq(prompt: str) -> tuple[str, int, int]:
    """Returns (text, tokens_in, tokens_out)."""
    from groq import AsyncGroq  # noqa: PLC0415
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    completion = await client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
    )
    text = completion.choices[0].message.content or ""
    usage = getattr(completion, "usage", None)
    tokens_in  = getattr(usage, "prompt_tokens",     0) or 0
    tokens_out = getattr(usage, "completion_tokens", 0) or 0
    return text, tokens_in, tokens_out


def _static_fallback() -> str:
    return (
        '{"summary": "AI insights require a GEMINI_API_KEY or GROQ_API_KEY in your .env '
        'file. Upload department data and configure an API key to enable live analysis.", '
        '"insights": []}'
    )


# ── Usage tracking ─────────────────────────────────────────────────────────────


def _fire_usage(**kwargs: Any) -> None:
    """Schedule ai_usage write as a fire-and-forget task."""
    try:
        from app.core.ai_usage import record_ai_usage  # noqa: PLC0415
        asyncio.ensure_future(record_ai_usage(**kwargs))
    except Exception:
        pass  # Never crash the caller over a metrics write
