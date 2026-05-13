"""SQLAlchemy ORM models for the NUAR Harmonised Data Model tables (UN-001-prep).

Alembic migration: alembic/versions/0003_nuar_schema.py

ADR-024: geometry columns use EPSG:4326 (WGS84), NOT the canonical NUAR
EPSG:27700. All BNG coordinates must pass through transform_bng_to_wgs84()
at the service layer before being written here.

ADR-007: NUARAsset.geometry is populated ONLY by the synthetic data generator
(Track 2, UN-008) for Phase 4 development. Live NUAR geometry queried from the
NUAR API is cached in memory (1h max) and NEVER written to this table.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class NUARAssetOwner(Base):
    """Asset owner / data provider — maps to nuarorganisations in canonical schema."""

    __tablename__ = "nuar_asset_owners"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    asset_type: Mapped[str] = mapped_column(Text, nullable=False)
    contact_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    asset_types: Mapped[list["NUARAssetType"]] = relationship(back_populates="owner")
    assets: Mapped[list["NUARAsset"]] = relationship(back_populates="owner")

    def __repr__(self) -> str:
        return f"<NUARAssetOwner {self.name} ({self.asset_type})>"


class NUARAssetType(Base):
    """Asset type code — controlled vocabulary per the NUAR codelist register."""

    __tablename__ = "nuar_asset_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("nuar_asset_owners.id"), nullable=False
    )
    type_code: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    owner: Mapped["NUARAssetOwner"] = relationship(back_populates="asset_types")
    assets: Mapped[list["NUARAsset"]] = relationship(back_populates="asset_type")

    def __repr__(self) -> str:
        return f"<NUARAssetType {self.type_code}>"


class NUARAsset(Base):
    """Underground utility asset.

    ADR-007: geometry column stores ONLY synthetic (data_source='synthetic') or
    sandbox (data_source='sandbox') data for Phase 4 development. Live NUAR
    geometry is NEVER persisted — query on demand, cache in memory 1h max.
    """

    __tablename__ = "nuar_underground_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_asset_id: Mapped[str] = mapped_column(Text, nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("nuar_asset_owners.id"), nullable=False
    )
    asset_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("nuar_asset_types.id"), nullable=False
    )

    # ADR-024: EPSG:4326 — canonical NUAR uses EPSG:27700; transform at service boundary
    geometry: Mapped[object] = mapped_column(
        Geometry("GEOMETRY", srid=4326, spatial_index=False),
        nullable=False,
    )

    depth_metres: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure_tier: Mapped[str | None] = mapped_column(Text, nullable=True)
    voltage_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    installation_date: Mapped[date | None] = mapped_column(nullable=True)
    last_verified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_source: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    owner: Mapped["NUARAssetOwner"] = relationship(back_populates="assets")
    asset_type: Mapped["NUARAssetType"] = relationship(back_populates="assets")

    __table_args__ = (
        Index("ix_nuar_underground_assets_geometry", "geometry", postgresql_using="gist"),
        Index("ix_nuar_underground_assets_owner", "owner_id"),
        Index("ix_nuar_underground_assets_data_source", "data_source"),
    )

    def __repr__(self) -> str:
        return f"<NUARAsset {self.external_asset_id} ({self.data_source})>"


class NUARStrikeRisk(Base):
    """Derived strike risk score per permit reference.

    ADR-007 compliant: contains only computed risk metrics, no asset geometry.
    Linked to street_works via permit_reference (soft text reference — no hard
    FK so strike risk records survive work record deletions).
    """

    __tablename__ = "nuar_strike_risks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    permit_reference: Mapped[str] = mapped_column(Text, nullable=False)
    overall_risk: Mapped[str] = mapped_column(Text, nullable=False)
    asset_count: Mapped[int] = mapped_column(Integer, nullable=False)
    assets_by_type: Mapped[dict] = mapped_column(JSON, nullable=False)
    highest_risk_asset: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_nuar_strike_risks_permit", "permit_reference"),
        Index("ix_nuar_strike_risks_overall_risk", "overall_risk"),
    )

    def __repr__(self) -> str:
        return f"<NUARStrikeRisk {self.permit_reference} {self.overall_risk}>"
