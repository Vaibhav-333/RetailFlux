"""Inventory intelligence ORM models."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = {"schema": "app"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.companies.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    contact_email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lead_days_target: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    otd_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    defect_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)
    tier: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    sku_suppliers: Mapped[list["SkuSupplier"]] = relationship(
        "SkuSupplier", back_populates="supplier", cascade="all, delete-orphan"
    )


class SkuMaster(Base):
    __tablename__ = "sku_master"
    __table_args__ = (
        UniqueConstraint("company_id", "sku", name="uq_sku_master_company_sku"),
        {"schema": "app"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.companies.id"), nullable=False
    )
    sku: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subcategory: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    season: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    abc_class: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    xyz_class: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    lifecycle_stage: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    launched_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_sold_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="active", server_default="active"
    )
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    sku_suppliers: Mapped[list["SkuSupplier"]] = relationship(
        "SkuSupplier", back_populates="sku", cascade="all, delete-orphan"
    )


class SkuSupplier(Base):
    __tablename__ = "sku_suppliers"
    __table_args__ = {"schema": "app"}

    sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.sku_master.id", ondelete="CASCADE"), primary_key=True
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.suppliers.id", ondelete="CASCADE"), primary_key=True
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    lead_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    sku: Mapped["SkuMaster"] = relationship("SkuMaster", back_populates="sku_suppliers")
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="sku_suppliers")
