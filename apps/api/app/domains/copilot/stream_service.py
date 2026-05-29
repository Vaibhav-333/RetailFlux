"""Streaming copilot service.

Pipeline per request:
  1. Check daily token cap.
  2. Get / create conversation.
  3. RAG retrieval from pgvector.
  4. Route user message to the best tool.
  5. Execute tool → format data.
  6. Build system prompt (persona + RAG context + conversation history).
  7. Stream response from Gemini (via thread + queue bridge) → yield SSE events.
  8. Persist user message + assistant response.
  9. Trigger conversation compaction if needed.
  10. Yield final [DONE] event with metadata.

SSE event format:
  data: {"type": "token", "content": "..."}\n\n
  data: {"type": "tool_used", "tool": "..."}\n\n
  data: {"type": "context_sources", "sources": [...]}\n\n
  data: {"type": "proposed_actions", "actions": [...]}\n\n
  data: {"type": "done", "message_id": "...", "provider": "..."}\n\n
  data: {"type": "error", "message": "..."}\n\n
"""
from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.prompt_guard import REFUSAL_RESPONSE, is_injection_attempt, sanitize_user_message
from app.domains.copilot.memory import (
    add_message,
    compact_if_needed,
    get_or_create_conversation,
    get_recent_messages_for_prompt,
)
from app.domains.copilot.retriever import retrieve_context
from app.domains.copilot.tool_router import build_tool_menu, get_tools_for_role
from app.domains.copilot.usage import check_and_record_usage

logger = structlog.get_logger()

# ── System persona ────────────────────────────────────────────────────────────

SYSTEM_PERSONA = """You are RetailFlux Copilot, an expert AI assistant embedded in RetailFlux,
an enterprise retail analytics OS. You have access to real-time sales, marketing, operations,
finance, procurement, inventory, and task data for this company.

Principles:
- Be concise and executive-friendly (under 200 words unless asked for detail).
- Always cite specific numbers from the data retrieved.
- Flag anomalies or risks proactively.
- For destructive actions (delete, bulk update), always ask for explicit confirmation.
- If proposing actions the user can take in RetailFlux, include them in the proposed_actions list.
"""

SAFETY_GUARD = """
SAFETY RULE: You must NEVER take destructive actions (delete records, override approvals,
modify financial data) without the user explicitly confirming with "yes, proceed" or similar.
Always explain consequences before proposing irreversible actions.
"""


# ── SSE helpers ───────────────────────────────────────────────────────────────


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _parse_tool_selection(text: str) -> dict | None:
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


# ── Gemini streaming bridge ───────────────────────────────────────────────────


async def _stream_gemini_text(prompt: str) -> AsyncGenerator[str, None]:
    """Stream text chunks from Gemini using a thread + asyncio.Queue bridge.

    Falls back to Groq (non-streaming) or a static error if unavailable.
    """
    if not settings.GEMINI_API_KEY:
        if settings.GROQ_API_KEY:
            # Groq: non-streaming; yield full response as one chunk
            try:
                from app.core.gemini import _call_groq  # noqa: PLC0415
                full = await _call_groq(prompt)
                yield full
                return
            except Exception:
                pass
        yield "I'm unable to generate a response right now (no AI provider configured)."
        return

    q: asyncio.Queue[str | None] = asyncio.Queue(maxsize=200)
    loop = asyncio.get_event_loop()

    def _sync_stream() -> None:
        try:
            import google.generativeai as genai  # noqa: PLC0415
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            response = model.generate_content(prompt, stream=True)
            for chunk in response:
                text_part = getattr(chunk, "text", None) or ""
                if text_part:
                    asyncio.run_coroutine_threadsafe(q.put(text_part), loop).result(timeout=10)
        except Exception as exc:
            asyncio.run_coroutine_threadsafe(q.put(f"__ERR__: {exc}"), loop).result(timeout=5)
        finally:
            asyncio.run_coroutine_threadsafe(q.put(None), loop).result(timeout=5)

    asyncio.get_event_loop().run_in_executor(None, _sync_stream)

    full_text = []
    while True:
        try:
            chunk = await asyncio.wait_for(q.get(), timeout=30)
        except asyncio.TimeoutError:
            break
        if chunk is None:
            break
        if chunk.startswith("__ERR__: "):
            logger.warning("gemini_stream_error", error=chunk)
            yield chunk.removeprefix("__ERR__: ")
            break
        full_text.append(chunk)
        yield chunk


# ── Core streaming pipeline ───────────────────────────────────────────────────


async def stream_copilot_response(
    db: AsyncSession,
    *,
    user_id: str,
    company_id: str,
    role: str,
    message: str,
    page_context: dict[str, Any] | None = None,
    conversation_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """Orchestrate the full copilot pipeline and yield SSE events."""

    # 1. Token cap check
    allowed, cap_msg = await check_and_record_usage(
        db, company_id=company_id, estimated_tokens=500
    )
    if not allowed:
        yield _sse({"type": "error", "message": cap_msg})
        yield _sse({"type": "done", "message_id": None, "provider": "system"})
        return

    # 1b. Prompt injection guard — reject before any LLM call
    if is_injection_attempt(message):
        yield _sse({"type": "token", "content": REFUSAL_RESPONSE})
        yield _sse({"type": "done", "message_id": None, "provider": "system"})
        return

    # Sanitize remaining control tokens (belt-and-suspenders after the guard above)
    message = sanitize_user_message(message)

    # 2. Get / create conversation
    conv_id = await get_or_create_conversation(
        db,
        user_id=user_id,
        company_id=company_id,
        conversation_id=conversation_id,
    )

    # 3. RAG retrieval
    rag_context, rag_sources = await retrieve_context(
        db,
        query=message,
        company_id=company_id,
        n=4,
    )

    if rag_sources:
        yield _sse({"type": "context_sources", "sources": rag_sources})

    # 4. Tool selection
    tools = get_tools_for_role(role)
    tool_menu = build_tool_menu(tools)

    page_ctx_str = ""
    if page_context:
        page_ctx_str = (
            "[Current page context]\n"
            + "\n".join(f"  {k}: {v}" for k, v in page_context.items())
            + "\n\n"
        )

    selection_prompt = (
        f"{SYSTEM_PERSONA}\n\n"
        f"{page_ctx_str}"
        f"Available data tools:\n{tool_menu}\n\n"
        f'User question: "{message}"\n\n'
        "Choose the best tool. Respond ONLY with valid JSON (no markdown):\n"
        '{"tool": "<tool_name>"} or {"tool": null, "direct_answer": "<your answer>"}'
    )

    try:
        from app.core.gemini import generate_text  # noqa: PLC0415
        selection_text, _ = await generate_text(selection_prompt)
        parsed = _parse_tool_selection(selection_text)
    except Exception:
        parsed = None

    tool_name: str | None = None
    tool_data: dict | None = None

    if parsed and parsed.get("tool") and parsed["tool"] in tools:
        tool_name = parsed["tool"]
        yield _sse({"type": "tool_used", "tool": tool_name})

        try:
            result = await tools[tool_name]["fn"](company_id)
            tool_data = result.model_dump() if hasattr(result, "model_dump") else result
        except Exception as exc:
            logger.warning("tool_execution_failed", tool=tool_name, error=str(exc))
            tool_data = None

    # 5. Build answer prompt
    history = await get_recent_messages_for_prompt(db, conversation_id=conv_id, max_tokens=2000)
    history_str = ""
    if history:
        lines = []
        for msg in history[-8:]:  # last 8 messages
            prefix = "User" if msg["role"] == "user" else "Copilot"
            lines.append(f"{prefix}: {msg['content'][:400]}")
        history_str = "\n".join(lines) + "\n\n"

    data_section = ""
    if tool_data:
        data_json = json.dumps(tool_data, default=str)[:3000]
        data_section = f"[Data from {tool_name}]\n{data_json}\n\n"
    elif parsed and parsed.get("direct_answer"):
        # LLM already answered; stream it directly
        direct = parsed["direct_answer"]
        yield _sse({"type": "token", "content": direct})
        msg_id = await add_message(
            db,
            conversation_id=conv_id,
            role="user",
            content=message,
        )
        await add_message(
            db,
            conversation_id=conv_id,
            role="assistant",
            content=direct,
            rag_sources=rag_sources,
            provider="gemini",
        )
        yield _sse({"type": "done", "message_id": msg_id, "provider": "gemini"})
        return

    answer_prompt = (
        f"{SYSTEM_PERSONA}\n{SAFETY_GUARD}\n\n"
        f"{page_ctx_str}"
        f"{rag_context}\n\n"
        f"{history_str}"
        f"{data_section}"
        f'User question: "{message}"\n\n'
        "Provide a concise, data-grounded answer. "
        "At the end, if there is a concrete action the user could take inside RetailFlux "
        '(e.g. accept a reorder, create a task, view a dashboard), append exactly one line:\n'
        'ACTION: <verb> | <description> | <url_path>\n'
        "Example: ACTION: view | See reorder queue | /dashboard/inventory\n"
        "If no action applies, omit the ACTION line entirely."
    )

    # 6. Stream response
    full_response: list[str] = []
    provider = "gemini" if settings.GEMINI_API_KEY else "groq"

    async for chunk in _stream_gemini_text(answer_prompt):
        full_response.append(chunk)
        yield _sse({"type": "token", "content": chunk})

    full_text = "".join(full_response)

    # 7. Extract proposed actions from response
    proposed_actions = _extract_actions(full_text)
    if proposed_actions:
        yield _sse({"type": "proposed_actions", "actions": proposed_actions})

    # 8. Persist messages
    await add_message(
        db,
        conversation_id=conv_id,
        role="user",
        content=message,
    )
    msg_id = await add_message(
        db,
        conversation_id=conv_id,
        role="assistant",
        content=full_text,
        tool_used=tool_name,
        rag_sources=rag_sources,
        proposed_actions=proposed_actions,
        provider=provider,
    )

    # 9. Compact if needed (fire-and-forget style via task)
    asyncio.ensure_future(compact_if_needed(db, conversation_id=conv_id))

    yield _sse({"type": "done", "message_id": msg_id, "provider": provider})


def _extract_actions(text: str) -> list[dict[str, str]]:
    """Parse ACTION: verb | description | url_path lines from the LLM response."""
    actions = []
    for line in text.splitlines():
        if line.strip().startswith("ACTION:"):
            parts = line.split("ACTION:", 1)[1].strip().split("|")
            if len(parts) >= 2:
                actions.append(
                    {
                        "verb": parts[0].strip(),
                        "description": parts[1].strip() if len(parts) > 1 else "",
                        "url_path": parts[2].strip() if len(parts) > 2 else "",
                    }
                )
    return actions
