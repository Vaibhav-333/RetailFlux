"""Notification domain service — async CRUD via SQLAlchemy."""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.schemas.notification import NotificationListResponse, NotificationOut


async def list_notifications(
    user_id: uuid.UUID,
    db: AsyncSession,
    limit: int = 20,
) -> NotificationListResponse:
    """Return the most recent notifications for a user, newest first."""
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    notifications = result.scalars().all()

    unread = sum(1 for n in notifications if n.read_at is None)

    return NotificationListResponse(
        items=[NotificationOut.model_validate(n) for n in notifications],
        unread_count=unread,
    )


async def mark_read(
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> bool:
    """Mark a notification as read. Returns False if not found / not owned."""
    result = await db.execute(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(timezone.utc))
        .returning(Notification.id)
    )
    await db.commit()
    return result.scalar() is not None


async def mark_all_read(user_id: uuid.UUID, db: AsyncSession) -> int:
    """Mark every unread notification for a user as read. Returns count updated."""
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return result.rowcount


async def create_notification(
    user_id: uuid.UUID,
    type_: str,
    payload: dict[str, Any],
    db: AsyncSession,
) -> NotificationOut:
    """Create a new notification for a user."""
    notif = Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        type=type_,
        payload=payload,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return NotificationOut.model_validate(notif)
