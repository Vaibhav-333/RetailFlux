"""Notifications endpoints — GET /notifications, PATCH /{id}/read, POST /read-all."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.dependencies import get_current_user
from app.domains.notifications.service import list_notifications, mark_all_read, mark_read
from app.models.user import User
from app.schemas.notification import NotificationListResponse

router = APIRouter()


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationListResponse:
    """List the most recent notifications for the authenticated user."""
    return await list_notifications(current_user.id, db, limit=limit)


@router.patch("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def read_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Mark a single notification as read."""
    found = await mark_read(notification_id, current_user.id, db)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or already read",
        )


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def read_all_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Mark all unread notifications as read for the authenticated user."""
    await mark_all_read(current_user.id, db)
