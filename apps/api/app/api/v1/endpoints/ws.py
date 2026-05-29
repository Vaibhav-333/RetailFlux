"""WebSocket endpoint — real-time push via Redis pub/sub."""
import asyncio
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging_setup import logger
from app.core.pubsub import CHANNEL_PREFIX
from app.core.security import decode_token
from app.models.user import User

router = APIRouter()

PING_INTERVAL = 25  # seconds — keeps alive under most proxy/LB timeouts


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
) -> None:
    """
    Authenticated WebSocket. Connect with ?token=<access_token>.
    Relays company-scoped events published by Celery workers.
    """
    # ── Auth ──────────────────────────────────────────────────────────────────
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4001)
            return
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        await websocket.close(code=4001)
        return

    # ── Resolve company_id from DB ────────────────────────────────────────────
    async with AsyncSessionLocal() as db:
        user = await db.scalar(
            select(User).where(User.id == user_id, User.is_active == True)  # noqa: E712
        )
    if not user:
        await websocket.close(code=4001)
        return

    company_id = str(user.company_id)
    await websocket.accept()
    logger.info("ws_connected", user_id=str(user_id), company_id=company_id)

    # ── Dedicated Redis connection (shared pool can't block on subscribe) ─────
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    channel = f"{CHANNEL_PREFIX}:{company_id}"
    await pubsub.subscribe(channel)
    ping_task: asyncio.Task | None = None

    try:
        ping_task = asyncio.create_task(_ping_loop(websocket))
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("ws_relay_error", error=str(exc))
    finally:
        if ping_task:
            ping_task.cancel()
        await pubsub.unsubscribe(channel)
        await r.aclose()
        logger.info("ws_disconnected", user_id=str(user_id))


async def _ping_loop(websocket: WebSocket) -> None:
    while True:
        await asyncio.sleep(PING_INTERVAL)
        try:
            await websocket.send_text('{"type":"ping"}')
        except Exception:
            break
