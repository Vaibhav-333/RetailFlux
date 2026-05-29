"""Notification ORM model — maps to app.notifications table (created in migration 0001)."""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("app.users.id"), nullable=False)
    type = Column(String(50), nullable=False)  # "info" | "warning" | "critical"
    payload = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
