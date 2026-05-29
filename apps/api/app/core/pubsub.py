"""Redis pub/sub helpers for real-time cross-process event broadcasting."""
import json

from app.core.config import settings
from app.core.logging_setup import logger

CHANNEL_PREFIX = "retailflux:events"


async def publish_event(company_id: str, event_type: str, data: dict) -> None:
    """Async publish for FastAPI routes. Creates a short-lived connection."""
    try:
        import redis.asyncio as aioredis  # noqa: PLC0415

        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        payload = json.dumps({"type": event_type, "data": data})
        await r.publish(f"{CHANNEL_PREFIX}:{company_id}", payload)
        await r.aclose()
    except Exception as exc:
        logger.warning("pubsub_publish_failed", error=str(exc))


def publish_event_sync(company_id: str, event_type: str, data: dict) -> None:
    """Sync publish for Celery tasks (no event loop required)."""
    try:
        import redis as sync_redis  # noqa: PLC0415

        r = sync_redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.publish(f"{CHANNEL_PREFIX}:{company_id}", json.dumps({"type": event_type, "data": data}))
        r.close()
    except Exception as exc:
        logger.warning("pubsub_publish_sync_failed", error=str(exc))
