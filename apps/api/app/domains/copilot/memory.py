"""Conversation memory — persistence in Postgres + summary compaction.

Each conversation thread stores messages in app.conversation_messages.
When the cumulative token estimate exceeds COMPACT_THRESHOLD, the earliest
messages are summarised by the LLM and replaced with a single system summary.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.gemini import generate_text

logger = structlog.get_logger()

COMPACT_THRESHOLD = 6000  # estimated tokens before compaction triggers
CHARS_PER_TOKEN = 4        # rough approximation: 1 token ≈ 4 chars


def _estimate_tokens(content: str) -> int:
    return max(1, len(content) // CHARS_PER_TOKEN)


# ── Conversation CRUD ─────────────────────────────────────────────────────────


async def get_or_create_conversation(
    db: AsyncSession,
    *,
    user_id: str,
    company_id: str,
    conversation_id: str | None = None,
) -> str:
    """Return an existing conversation UUID or create a new one.

    If *conversation_id* is provided and belongs to the user, it is returned as-is.
    """
    if conversation_id:
        row = await db.execute(
            text(
                "SELECT id FROM app.conversations "
                "WHERE id = :cid AND user_id = :uid AND company_id = :compid"
            ),
            {"cid": conversation_id, "uid": user_id, "compid": company_id},
        )
        existing = row.fetchone()
        if existing:
            return str(existing[0])

    # Create new
    new_id = str(uuid.uuid4())
    try:
        await db.execute(
            text(
                "INSERT INTO app.conversations (id, company_id, user_id) "
                "VALUES (:id, :compid, :uid)"
            ),
            {"id": new_id, "compid": company_id, "uid": user_id},
        )
        await db.commit()
    except Exception as exc:
        logger.warning("create_conversation_failed", error=str(exc))
        await db.rollback()
    return new_id


async def list_conversations(
    db: AsyncSession,
    *,
    user_id: str,
    company_id: str,
    limit: int = 20,
    offset: int = 0,
) -> list[dict[str, Any]]:
    result = await db.execute(
        text("""
            SELECT id, title, summary, message_count, total_tokens,
                   last_message_at, created_at
            FROM app.conversations
            WHERE user_id = :uid AND company_id = :compid
            ORDER BY last_message_at DESC NULLS LAST, created_at DESC
            LIMIT :lim OFFSET :off
        """),
        {"uid": user_id, "compid": company_id, "lim": limit, "off": offset},
    )
    rows = result.fetchall()
    return [
        {
            "id": str(r[0]),
            "title": r[1],
            "summary": r[2],
            "message_count": r[3],
            "total_tokens": r[4],
            "last_message_at": r[5].isoformat() if r[5] else None,
            "created_at": r[6].isoformat() if r[6] else None,
        }
        for r in rows
    ]


async def get_conversation_messages(
    db: AsyncSession,
    *,
    conversation_id: str,
    user_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    result = await db.execute(
        text("""
            SELECT m.id, m.role, m.content, m.tool_used, m.rag_sources,
                   m.proposed_actions, m.token_estimate, m.provider, m.created_at
            FROM app.conversation_messages m
            JOIN app.conversations c ON c.id = m.conversation_id
            WHERE m.conversation_id = :cid AND c.user_id = :uid
            ORDER BY m.created_at
            LIMIT :lim
        """),
        {"cid": conversation_id, "uid": user_id, "lim": limit},
    )
    rows = result.fetchall()
    return [
        {
            "id": str(r[0]),
            "role": r[1],
            "content": r[2],
            "tool_used": r[3],
            "rag_sources": r[4] or [],
            "proposed_actions": r[5] or [],
            "token_estimate": r[6],
            "provider": r[7],
            "created_at": r[8].isoformat() if r[8] else None,
        }
        for r in rows
    ]


async def add_message(
    db: AsyncSession,
    *,
    conversation_id: str,
    role: str,
    content: str,
    tool_used: str | None = None,
    rag_sources: list[dict] | None = None,
    proposed_actions: list[dict] | None = None,
    provider: str | None = None,
) -> str:
    """Insert a message and update conversation counters. Returns the message id."""
    import json as _json  # noqa: PLC0415

    msg_id = str(uuid.uuid4())
    tokens = _estimate_tokens(content)
    sources_json = _json.dumps(rag_sources or [])
    actions_json = _json.dumps(proposed_actions or [])

    try:
        await db.execute(
            text("""
                INSERT INTO app.conversation_messages
                    (id, conversation_id, role, content, tool_used,
                     rag_sources, proposed_actions, token_estimate, provider)
                VALUES
                    (:id, :cid, :role, :content, :tool,
                     CAST(:sources AS jsonb), CAST(:actions AS jsonb), :tokens, :provider)
            """),
            {
                "id": msg_id,
                "cid": conversation_id,
                "role": role,
                "content": content,
                "tool": tool_used,
                "sources": sources_json,
                "actions": actions_json,
                "tokens": tokens,
                "provider": provider,
            },
        )
        # Update conversation header
        await db.execute(
            text("""
                UPDATE app.conversations
                SET message_count = message_count + 1,
                    total_tokens  = total_tokens + :tokens,
                    last_message_at = NOW(),
                    updated_at = NOW()
                WHERE id = :cid
            """),
            {"cid": conversation_id, "tokens": tokens},
        )
        await db.commit()
    except Exception as exc:
        logger.warning("add_message_failed", error=str(exc))
        await db.rollback()

    return msg_id


async def get_recent_messages_for_prompt(
    db: AsyncSession,
    *,
    conversation_id: str,
    max_tokens: int = 4000,
) -> list[dict[str, str]]:
    """Return the most recent messages that fit within *max_tokens*, newest last.

    Returned format: [{"role": ..., "content": ...}] — ready for LLM prompt building.
    """
    result = await db.execute(
        text("""
            SELECT role, content, token_estimate
            FROM app.conversation_messages
            WHERE conversation_id = :cid
            ORDER BY created_at DESC
            LIMIT 40
        """),
        {"cid": conversation_id},
    )
    rows = list(result.fetchall())
    rows.reverse()  # chronological order

    selected: list[dict[str, str]] = []
    budget = max_tokens
    for role, content, tokens in rows:
        if budget <= 0:
            break
        selected.append({"role": role, "content": content})
        budget -= tokens

    return selected


# ── Compaction ────────────────────────────────────────────────────────────────


async def compact_if_needed(
    db: AsyncSession,
    *,
    conversation_id: str,
) -> bool:
    """If the conversation exceeds COMPACT_THRESHOLD tokens, summarise the oldest half.

    Returns True if compaction ran.
    """
    row = await db.execute(
        text("SELECT total_tokens FROM app.conversations WHERE id = :cid"),
        {"cid": conversation_id},
    )
    conv = row.fetchone()
    if not conv or conv[0] < COMPACT_THRESHOLD:
        return False

    # Grab the first half of messages to summarise
    result = await db.execute(
        text("""
            SELECT id, role, content
            FROM app.conversation_messages
            WHERE conversation_id = :cid
            ORDER BY created_at
        """),
        {"cid": conversation_id},
    )
    msgs = result.fetchall()
    if len(msgs) < 6:
        return False

    half = len(msgs) // 2
    to_summarise = msgs[:half]
    ids_to_delete = [str(r[0]) for r in to_summarise]

    dialogue = "\n".join(f"{r[1].upper()}: {r[2][:300]}" for r in to_summarise)
    summary_prompt = (
        "Summarise the following conversation excerpt for a retail analytics AI assistant. "
        "Keep it under 200 words and preserve key facts, numbers, and decisions.\n\n"
        f"{dialogue}"
    )
    try:
        summary_text, _ = await generate_text(summary_prompt)
    except Exception:
        return False

    try:
        # Insert system summary message at the front
        summary_id = str(uuid.uuid4())
        summary_tokens = _estimate_tokens(summary_text)
        deleted_tokens = sum(r[2] for r in [])  # we'll recalc below

        # Delete old messages
        ids_placeholder = ", ".join(f"'{eid}'" for eid in ids_to_delete)
        deleted_result = await db.execute(
            text(
                f"DELETE FROM app.conversation_messages WHERE id IN ({ids_placeholder}) "
                "RETURNING token_estimate"
            ),
        )
        deleted_tokens = sum(r[0] for r in deleted_result.fetchall())

        # Insert the summary as a system message with the oldest timestamp
        await db.execute(
            text("""
                INSERT INTO app.conversation_messages
                    (id, conversation_id, role, content, token_estimate)
                VALUES (:id, :cid, 'system', :content, :tokens)
            """),
            {
                "id": summary_id,
                "cid": conversation_id,
                "content": f"[Conversation summary]\n{summary_text}",
                "tokens": summary_tokens,
            },
        )
        # Adjust conversation token count
        token_delta = summary_tokens - deleted_tokens
        await db.execute(
            text("""
                UPDATE app.conversations
                SET total_tokens = GREATEST(0, total_tokens + :delta),
                    summary = :summary,
                    updated_at = NOW()
                WHERE id = :cid
            """),
            {"delta": token_delta, "summary": summary_text[:500], "cid": conversation_id},
        )
        await db.commit()
        logger.info("conversation_compacted", conversation_id=conversation_id)
        return True
    except Exception as exc:
        logger.warning("compaction_failed", error=str(exc))
        await db.rollback()
        return False


async def delete_conversation(
    db: AsyncSession,
    *,
    conversation_id: str,
    user_id: str,
) -> bool:
    """Hard-delete a conversation and all its messages. Returns True if deleted."""
    try:
        result = await db.execute(
            text(
                "DELETE FROM app.conversations "
                "WHERE id = :cid AND user_id = :uid "
                "RETURNING id"
            ),
            {"cid": conversation_id, "uid": user_id},
        )
        deleted = result.fetchone()
        await db.commit()
        return deleted is not None
    except Exception as exc:
        logger.warning("delete_conversation_failed", error=str(exc))
        await db.rollback()
        return False
