import enum
import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class UploadStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETE = "complete"
    REJECTED = "rejected"
    ERROR = "error"


class Upload(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "uploads"
    __table_args__ = {"schema": "app"}

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.companies.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.users.id"), nullable=False
    )
    dept: Mapped[str] = mapped_column(String(50), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=UploadStatus.QUEUED.value)
    rows_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rows_clean: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rows_rejected: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    ge_report_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
