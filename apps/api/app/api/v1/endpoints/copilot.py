"""Copilot endpoints.

Routes:
  POST /copilot/ask          Non-streaming chat (legacy, kept for backward compat)
  POST /copilot/stream       SSE streaming chat with RAG + conversation memory
  POST /copilot/explain/{resource}/{id}  AI explanation (cached)
  GET  /copilot/conversations            List user's conversation threads
  GET  /copilot/conversations/{id}       Thread detail with messages
  DELETE /copilot/conversations/{id}     Delete a conversation
  GET  /copilot/usage                    Today's token usage for this company
"""
import traceback
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

_log = structlog.get_logger()

from app.core.database import get_db
from app.core.limiter import limiter
from app.domains.auth.dependencies import get_current_user
from app.domains.chat.chat_service import handle_chat_message
from app.domains.copilot.explain_service import get_explanation
from app.domains.copilot.memory import (
    delete_conversation,
    get_conversation_messages,
    list_conversations,
)
from app.domains.copilot.stream_service import stream_copilot_response
from app.domains.copilot.usage import get_usage_today
from app.models.user import User

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class CopilotAskRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    page_context: dict[str, Any] | None = Field(
        default=None,
        description="Current page name, active filters, focused widget, etc.",
    )


class CopilotAskResponse(BaseModel):
    answer: str
    tool_used: str | None = None
    provider: str


class CopilotStreamRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    page_context: dict[str, Any] | None = None
    conversation_id: str | None = None


class ExplanationResponse(BaseModel):
    body: str
    resource: str
    resource_id: str
    cached: bool
    version: int


class ExplanationRequest(BaseModel):
    context: dict[str, Any] | None = None


# ── Non-streaming ask (backward compat) ───────────────────────────────────────


@router.post("/ask", response_model=CopilotAskResponse)
@limiter.limit("120/hour")
async def copilot_ask(
    request: Request,
    body: CopilotAskRequest,
    current_user: User = Depends(get_current_user),
) -> CopilotAskResponse:
    """Non-streaming copilot chat enriched with page context."""
    enriched_message = body.message
    if body.page_context:
        ctx_lines = [f"  {k}: {v}" for k, v in body.page_context.items()]
        enriched_message = f"[Page context]\n{chr(10).join(ctx_lines)}\n\n[User question]\n{body.message}"

    role = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    result = await handle_chat_message(
        company_id=str(current_user.company_id),
        role=role,
        message=enriched_message,
    )
    return CopilotAskResponse(answer=result.answer, tool_used=result.tool_used, provider=result.provider)


# ── SSE streaming endpoint ────────────────────────────────────────────────────


@router.post("/stream")
@limiter.limit("60/hour")
async def copilot_stream(
    request: Request,
    body: CopilotStreamRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Server-Sent Events streaming copilot with RAG, tool routing, and conversation memory.

    Each yielded line is an SSE event: ``data: {json}\\n\\n``

    Event types: token | tool_used | context_sources | proposed_actions | done | error
    """
    try:
        role = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    except Exception as exc:
        _log.error("stream_role_error", error=str(exc), tb=traceback.format_exc())
        raise

    _log.info("stream_starting", user=str(current_user.id), role=role, msg=body.message[:50])

    async def event_generator():
        try:
            async for chunk in stream_copilot_response(
                db,
                user_id=str(current_user.id),
                company_id=str(current_user.company_id),
                role=role,
                message=body.message,
                page_context=body.page_context,
                conversation_id=body.conversation_id,
            ):
                yield chunk
        except Exception as exc:
            _log.error("stream_generator_error", error=str(exc), tb=traceback.format_exc())
            yield f'data: {{"type":"error","message":"Internal error: {str(exc)[:100]}"}}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable Nginx proxy buffering
        },
    )


# ── Explanation cache ─────────────────────────────────────────────────────────


@router.post("/explain/{resource}/{resource_id}", response_model=ExplanationResponse)
@limiter.limit("200/hour")
async def explain_resource(
    request: Request,
    resource: str,
    resource_id: str,
    body: ExplanationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExplanationResponse:
    """Return an AI explanation for a resource, cached in app.explanations."""
    result = await get_explanation(
        db=db,
        resource=resource,
        resource_id=resource_id,
        context=body.context,
    )
    return ExplanationResponse(**result)


# ── Conversation management ───────────────────────────────────────────────────


@router.get("/conversations")
async def list_user_conversations(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List the current user's conversation threads, most recent first."""
    conversations = await list_conversations(
        db,
        user_id=str(current_user.id),
        company_id=str(current_user.company_id),
        limit=min(limit, 50),
        offset=offset,
    )
    return {"conversations": conversations, "total": len(conversations)}


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a conversation with its messages."""
    messages = await get_conversation_messages(
        db,
        conversation_id=conversation_id,
        user_id=str(current_user.id),
    )
    return {"conversation_id": conversation_id, "messages": messages}


@router.delete("/conversations/{conversation_id}")
async def remove_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a conversation and all its messages."""
    deleted = await delete_conversation(
        db,
        conversation_id=conversation_id,
        user_id=str(current_user.id),
    )
    if not deleted:
        from fastapi import HTTPException  # noqa: PLC0415
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}


# ── Usage stats ───────────────────────────────────────────────────────────────


@router.get("/usage")
async def copilot_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return today's token usage for this company."""
    return await get_usage_today(db, company_id=str(current_user.company_id))
