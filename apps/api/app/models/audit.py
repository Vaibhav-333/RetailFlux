"""AuditLog ORM model — maps to app.audit_log table."""
import uuid

from sqlalchemy import Column, DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(100), nullable=False, index=True)
    resource_id = Column(String(255), nullable=True)
    ip = Column(String(45), nullable=True)
    ua = Column(Text(), nullable=True)
    diff = Column(JSONB(), nullable=True)
    request_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), index=True)
