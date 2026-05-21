"""SQLAlchemy ORM models for D-TRO Traffic Regulation Orders (DT-001, ADR-027).

Alembic migration: alembic/versions/0005_dtro_schema.py

Stores permanent TROs and TTROs (Temporary Traffic Regulation Orders) in two
tables: dtro_orders (the order header) and dtro_provisions (individual spatial
restrictions within an order).

Schema conforms to D-TRO v4.0.0 JSON schema published at:
github.com/department-for-transport-public/D-TRO

ADR-024 applies: all geometry in EPSG:4326 (WGS84).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class DTROOrder(Base):
    """D-TRO Traffic Regulation Order header — top-level TRO record."""

    __tablename__ = "dtro_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dtro_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    schema_version: Mapped[str] = mapped_column(Text, nullable=False, default="4.0.0")
    reference_number: Mapped[str] = mapped_column(Text, nullable=False)
    tro_type: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    authority: Mapped[str] = mapped_column(Text, nullable=False)
    is_temporary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_source: Mapped[str] = mapped_column(Text, nullable=False)
    raw_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    provisions: Mapped[list["DTROProvision"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_dtro_orders_authority", "authority"),
        Index("ix_dtro_orders_tro_type", "tro_type"),
        Index("ix_dtro_orders_data_source", "data_source"),
        Index("ix_dtro_orders_valid_from", "valid_from"),
    )

    def __repr__(self) -> str:
        return f"<DTROOrder {self.reference_number} ({self.tro_type})>"


class DTROProvision(Base):
    """Individual spatial provision within a D-TRO order.

    Each provision carries the geometry (WGS84 LineString or Polygon) that
    defines where the restriction applies, plus type-specific attributes such
    as speed_mph for speed limit provisions.
    """

    __tablename__ = "dtro_provisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dtro_orders.id"), nullable=False
    )
    provision_type: Mapped[str] = mapped_column(Text, nullable=False)
    geometry: Mapped[object] = mapped_column(
        Geometry("GEOMETRY", srid=4326, spatial_index=False), nullable=False
    )
    speed_mph: Mapped[int | None] = mapped_column(Integer, nullable=True)
    restriction_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    conditions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    order: Mapped["DTROOrder"] = relationship(back_populates="provisions")

    __table_args__ = (
        Index("ix_dtro_provisions_geometry", "geometry", postgresql_using="gist"),
        Index("ix_dtro_provisions_order", "order_id"),
        Index("ix_dtro_provisions_type", "provision_type"),
    )

    def __repr__(self) -> str:
        return f"<DTROProvision {self.provision_type} on order {self.order_id}>"
