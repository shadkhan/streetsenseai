"""Repository layer for StreetWork database operations.

All database access for street works goes through this module.
Converts between the domain StreetWork (schemas/domain.py) and the
SQLAlchemy StreetWork row (models/street_work.py).

Geometry conversion uses shapely + geoalchemy2:
  - Writing: domain geometry -> WKTElement -> PostGIS
  - Reading: PostGIS WKBElement -> shapely shape -> domain geometry
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.street_work import StreetWork as StreetWorkRow
from schemas.domain import (
    LineStringGeometry,
    PointGeometry,
    StreetWork,
    StreetWorkStatus,
)

logger = logging.getLogger(__name__)


# ── Geometry helpers ───────────────────────────────────────────────────────────

def _geometry_to_wkt(geometry: PointGeometry | LineStringGeometry) -> WKTElement:
    if isinstance(geometry, PointGeometry):
        lng, lat = geometry.coordinates
        wkt = f"POINT({lng} {lat})"
    else:
        coords = ", ".join(f"{c[0]} {c[1]}" for c in geometry.coordinates)
        wkt = f"LINESTRING({coords})"
    return WKTElement(wkt, srid=4326)


def _wkb_to_geometry(wkb: object) -> PointGeometry | LineStringGeometry:
    shape = to_shape(wkb)  # type: ignore[arg-type]
    if shape.geom_type == "Point":
        return PointGeometry(type="Point", coordinates=(shape.x, shape.y))
    if shape.geom_type == "LineString":
        return LineStringGeometry(
            type="LineString",
            coordinates=[(c[0], c[1]) for c in shape.coords],
        )
    raise ValueError(f"Unsupported geometry type from DB: {shape.geom_type}")


# ── Date helpers ───────────────────────────────────────────────────────────────

def _to_date(s: str | None) -> date | None:
    if not s:
        return None
    return date.fromisoformat(s[:10])


def _to_datetime(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# ── Domain <-> Row conversion ──────────────────────────────────────────────────

def _domain_to_values(work: StreetWork) -> dict:
    """Convert a domain StreetWork to a dict suitable for INSERT/UPDATE."""
    start = _to_date(work.proposed_start_date)
    end = _to_date(work.proposed_end_date)
    if start is None or end is None:
        raise ValueError(
            f"Permit {work.permit_reference} has invalid date: "
            f"start={work.proposed_start_date} end={work.proposed_end_date}"
        )
    return {
        "permit_reference": work.permit_reference,
        "usrn": work.usrn,
        "street_name": work.street_name,
        "authority": work.authority,
        "promoter": work.promoter,
        "promoter_licence_number": work.promoter_licence_number,
        "work_type": work.work_type,
        "traffic_management_type": work.traffic_management_type,
        "restriction_type": work.restriction_type,
        "proposed_start_date": start,
        "proposed_end_date": end,
        "actual_start_date": _to_datetime(work.actual_start_date),
        "actual_end_date": _to_datetime(work.actual_end_date),
        "status": work.status,
        "risk_score": work.risk_score,
        "geometry": _geometry_to_wkt(work.geometry),
    }


def _row_to_domain(row: StreetWorkRow) -> StreetWork:
    """Convert a SQLAlchemy StreetWork row to the domain StreetWork model."""
    return StreetWork(
        permit_reference=row.permit_reference,
        usrn=row.usrn,
        street_name=row.street_name,
        authority=row.authority,
        promoter=row.promoter,
        promoter_licence_number=row.promoter_licence_number,
        work_type=row.work_type,
        traffic_management_type=row.traffic_management_type,
        restriction_type=row.restriction_type,
        proposed_start_date=str(row.proposed_start_date),
        proposed_end_date=str(row.proposed_end_date),
        actual_start_date=str(row.actual_start_date) if row.actual_start_date else None,
        actual_end_date=str(row.actual_end_date) if row.actual_end_date else None,
        status=row.status,  # type: ignore[arg-type]
        geometry=_wkb_to_geometry(row.geometry),
        risk_score=row.risk_score,  # type: ignore[arg-type]
    )


# ── Repository functions ───────────────────────────────────────────────────────

async def upsert_work(session: AsyncSession, work: StreetWork) -> None:
    """Insert a StreetWork, or update all fields if the permit_reference already exists.

    Called by tasks/ingest.py after every SM webhook or polling cycle.
    """
    values = _domain_to_values(work)
    stmt = pg_insert(StreetWorkRow).values(**values)
    update_values = {k: v for k, v in values.items() if k != "permit_reference"}
    stmt = stmt.on_conflict_do_update(
        index_elements=["permit_reference"],
        set_=update_values,
    )
    await session.execute(stmt)
    await session.commit()
    logger.debug("Upserted permit %s (status=%s)", work.permit_reference, work.status)


async def get_work_by_permit(
    session: AsyncSession, permit_reference: str
) -> StreetWork | None:
    """Fetch a single StreetWork by permit reference. Returns None if not found."""
    row = await session.get(StreetWorkRow, permit_reference)
    return _row_to_domain(row) if row is not None else None


async def get_works_by_bbox(
    session: AsyncSession,
    bbox: tuple[float, float, float, float],
    statuses: list[str] | None = None,
) -> list[StreetWork]:
    """Fetch all works whose geometry intersects the given bounding box.

    bbox: (min_lon, min_lat, max_lon, max_lat) in WGS-84.
    Optionally filter by status (e.g. ['granted', 'in_progress']).
    Used by SM-006 map query endpoints and Phase 2 corridor scoring.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
    stmt = select(StreetWorkRow).where(
        func.ST_Intersects(StreetWorkRow.geometry, envelope)
    )
    if statuses:
        stmt = stmt.where(StreetWorkRow.status.in_(statuses))

    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_domain(row) for row in rows]


async def get_works_by_usrn(
    session: AsyncSession, usrn: str
) -> list[StreetWork]:
    """Fetch all works on a specific street (USRN). Used by SM-003 and copilot."""
    stmt = select(StreetWorkRow).where(StreetWorkRow.usrn == usrn)
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_domain(row) for row in rows]


async def get_works_by_authority(
    session: AsyncSession,
    authority: str,
    statuses: list[str] | None = None,
) -> list[StreetWork]:
    """Fetch all works for a highway authority. Used by compliance analytics (SM-007)."""
    stmt = select(StreetWorkRow).where(StreetWorkRow.authority == authority)
    if statuses:
        stmt = stmt.where(StreetWorkRow.status.in_(statuses))
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_domain(row) for row in rows]
