import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class UserRole(str, enum.Enum):
    CEO = "ceo"
    ADMIN = "admin"
    SALES = "sales"
    MARKETING = "marketing"
    FINANCE = "finance"
    OPERATIONS = "operations"
    PROCUREMENT = "procurement"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = {"schema": "app"}

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        # Use explicit string values so asyncpg receives "ceo"/"admin"/… not "CEO"/"ADMIN"/…
        Enum(
            "ceo", "admin", "sales", "marketing", "finance", "operations", "procurement",
            name="userrole", schema="app", create_type=False,
        ),
        nullable=False,
        default=UserRole.SALES.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    prefs: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    onboarding_step: Mapped[int] = mapped_column(default=0, nullable=False, server_default="0")

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.companies.id"), nullable=False, index=True
    )
    company: Mapped["Company"] = relationship("Company", back_populates="users")
