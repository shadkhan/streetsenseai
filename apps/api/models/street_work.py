"""SQLAlchemy ORM model for Street Manager permit records.

Geometry is stored as a PostGIS GEOMETRY column (accepts Point and
LineString) with a GIST spatial index for fast bbox queries in SM-006.

Alembic migration: alembic/versions/0001_create_street_works.py
"""
from __future__ import annotations

from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import Date, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class StreetWork(Base):
    __tablename__ = "street_works"

    # Primary key — permit reference is the canonical SM identifier
    permit_reference: Mapped[str] = mapped_column(String, primary_key=True)

    # Street identity
    usrn: Mapped[str] = mapped_column(String, nullable=False)
    street_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    authority: Mapped[str] = mapped_column(String, nullable=False, default="")

    # Promoter
    promoter: Mapped[str] = mapped_column(String, nullable=False, default="")
    promoter_licence_number: Mapped[str] = mapped_column(String, nullable=False, default="")

    # Works classification
    work_type: Mapped[str] = mapped_column(String, nullable=False, default="")
    traffic_management_type: Mapped[str] = mapped_column(String, nullable=False, default="")
    restriction_type: Mapped[str] = mapped_column(String, nullable=False, default="")

    # Dates — stored as Date/DateTime for proper range queries
    proposed_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    proposed_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Status and risk
    status: Mapped[str] = mapped_column(String, nullable=False)
    risk_score: Mapped[str | None] = mapped_column(String, nullable=True)

    # PostGIS geometry — GIST index created automatically by spatial_index=True
    geometry: Mapped[object] = mapped_column(
        Geometry("GEOMETRY", srid=4326, spatial_index=True),
        nullable=False,
    )

    # Audit timestamps
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
        Index("ix_street_works_usrn", "usrn"),
        Index("ix_street_works_status", "status"),
        Index("ix_street_works_authority", "authority"),
        # Composite index for date-range queries used by SM-006
        Index("ix_street_works_dates", "proposed_start_date", "proposed_end_date"),
    )

    def __repr__(self) -> str:
        return f"<StreetWork {self.permit_reference} {self.status}>"
