"""SQLAlchemy ORM model for corridor definitions (CR-001).

Corridors are named road segments (e.g. "A38 — Birmingham City Centre")
stored as PostGIS LineString geometries. Risk scoring fields (risk_level,
risk_score) are populated by CR-003/CR-004 and start as NULL.
"""
from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Corridor(Base):
    __tablename__ = "corridors"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    road_classification: Mapped[str] = mapped_column(String, nullable=False)

    # PostGIS LineString geometry — GIST index for bbox queries (CR-002)
    geometry: Mapped[object] = mapped_column(
        Geometry("LINESTRING", srid=4326, spatial_index=True),
        nullable=False,
    )

    # Risk fields — NULL until CR-003/CR-004 populate them
    risk_level: Mapped[str | None] = mapped_column(String, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_calculated: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Provenance: "os_open_roads" or "synthetic"
    source: Mapped[str] = mapped_column(String, nullable=False, default="synthetic")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_corridors_road_classification", "road_classification"),
        Index("ix_corridors_risk_level", "risk_level"),
    )

    def __repr__(self) -> str:
        return f"<Corridor {self.id} ({self.road_classification}) risk={self.risk_level}>"
