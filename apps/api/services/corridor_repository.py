"""Repository layer for corridor database operations (CR-001 to CR-004).

All database access for corridors goes through this module.
Converts between the domain CorridorBase (schemas/corridor.py) and the
SQLAlchemy Corridor row (models/corridor.py).

Geometry conversion: domain LineStringGeometry <-> PostGIS WKB/WKT.
"""
from __future__ import annotations

import logging
from datetime import date as DateType, datetime, timezone

from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.corridor import Corridor as CorridorRow
from schemas.corridor import CorridorBase, CorridorRead, RoadClassification
from schemas.domain import LineStringGeometry

logger = logging.getLogger(__name__)


# ── Geometry helpers ───────────────────────────────────────────────────────────

def _linestring_to_wkt(coordinates: list[tuple[float, float]]) -> WKTElement:
    coords_str = ", ".join(f"{c[0]} {c[1]}" for c in coordinates)
    return WKTElement(f"LINESTRING({coords_str})", srid=4326)


def _wkb_to_linestring(wkb: object) -> list[tuple[float, float]]:
    shape = to_shape(wkb)  # type: ignore[arg-type]
    return [(round(c[0], 6), round(c[1], 6)) for c in shape.coords]


# ── Domain <-> Row conversion ──────────────────────────────────────────────────

def _domain_to_values(corridor: CorridorBase) -> dict:
    return {
        "id": corridor.id,
        "name": corridor.name,
        "road_classification": corridor.road_classification,
        "geometry": _linestring_to_wkt(corridor.geometry.coordinates),
        "source": corridor.source,
    }


def _row_to_domain(row: CorridorRow) -> CorridorRead:
    from schemas.domain import LineStringGeometry
    coords = _wkb_to_linestring(row.geometry)
    classification: RoadClassification = row.road_classification  # type: ignore[assignment]
    return CorridorRead(
        id=row.id,
        name=row.name,
        road_classification=classification,
        geometry=LineStringGeometry(type="LineString", coordinates=coords),
        source=row.source,
        risk_level=row.risk_level,  # type: ignore[arg-type]
        risk_score=row.risk_score,
        last_calculated=row.last_calculated.isoformat() if row.last_calculated else None,
    )


# ── Repository functions ───────────────────────────────────────────────────────

async def upsert_corridor(session: AsyncSession, corridor: CorridorBase) -> None:
    """Insert or update a corridor record keyed by id."""
    values = _domain_to_values(corridor)
    stmt = pg_insert(CorridorRow).values(**values)
    update_cols = {k: v for k, v in values.items() if k != "id"}
    stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update_cols)
    await session.execute(stmt)
    await session.commit()
    logger.debug("Upserted corridor %s (%s)", corridor.id, corridor.source)


async def get_corridor_by_id(session: AsyncSession, corridor_id: str) -> CorridorRead | None:
    """Return a single corridor by its slug ID, or None if not found."""
    row = await session.get(CorridorRow, corridor_id)
    return _row_to_domain(row) if row is not None else None


async def get_all_corridors(session: AsyncSession) -> list[CorridorRead]:
    """Return all corridors ordered by name."""
    rows = (
        await session.execute(select(CorridorRow).order_by(CorridorRow.name))
    ).scalars().all()
    return [_row_to_domain(row) for row in rows]


async def get_corridors_by_bbox(
    session: AsyncSession,
    bbox: tuple[float, float, float, float],
) -> list[CorridorRead]:
    """Return corridors whose geometry intersects the given WGS-84 bbox.

    bbox: (min_lon, min_lat, max_lon, max_lat)
    Used by CR-005 map interface to load visible corridors.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
    rows = (
        await session.execute(
            select(CorridorRow).where(
                func.ST_Intersects(CorridorRow.geometry, envelope)
            )
        )
    ).scalars().all()
    return [_row_to_domain(row) for row in rows]


async def count_corridors(session: AsyncSession) -> int:
    """Return total number of corridor records."""
    result = await session.execute(select(func.count()).select_from(CorridorRow))
    return int(result.scalar_one())


async def save_corridor_risk(
    session: AsyncSession,
    corridor_id: str,
    risk_score: float,
    risk_level: str,
) -> None:
    """Persist computed risk score and level back to the corridor row (CR-003/004).

    Called by the background Celery task (tasks/risk_tasks.py) after each
    scoring run.  The list endpoint serves these stored values so it never
    needs to re-run spatial queries for all corridors.
    """
    await session.execute(
        update(CorridorRow)
        .where(CorridorRow.id == corridor_id)
        .values(
            risk_score=risk_score,
            risk_level=risk_level,
            last_calculated=datetime.now(timezone.utc),
        )
    )
    await session.commit()
    logger.debug("Saved risk for corridor %s: %.1f (%s)", corridor_id, risk_score, risk_level)


async def get_corridor_with_risk(
    session: AsyncSession,
    corridor_id: str,
    window_start: DateType | None = None,
    window_end: DateType | None = None,
) -> CorridorRead | None:
    """Return a single corridor with live-computed risk data (CR-002/003/004).

    Runs the full scoring pipeline on every call — intended for the
    GET /corridors/{id} detail endpoint where freshness matters.
    The list endpoint (get_all_corridors) serves stored values instead.
    window_start/window_end optionally restrict scoring to a date window (CR-007).
    """
    # Lazy import avoids a circular dependency (corridor_risk imports corridor models
    # but not corridor_repository)
    from services.corridor_risk import score_corridor

    row = await session.get(CorridorRow, corridor_id)
    if row is None:
        return None

    risk_score, risk_level, risk_factors, works = await score_corridor(
        session, corridor_id, window_start=window_start, window_end=window_end
    )

    active_count = sum(1 for w in works if w.status == "in_progress")
    planned_count = sum(1 for w in works if w.status in ("submitted", "granted"))

    coords = _wkb_to_linestring(row.geometry)
    classification: RoadClassification = row.road_classification  # type: ignore[assignment]
    return CorridorRead(
        id=row.id,
        name=row.name,
        road_classification=classification,
        geometry=LineStringGeometry(type="LineString", coordinates=coords),
        source=row.source,
        risk_level=risk_level,
        risk_score=risk_score,
        risk_factors=risk_factors,
        concurrent_works=works,
        active_works_count=active_count,
        planned_works_count=planned_count,
        last_calculated=datetime.now(timezone.utc).isoformat(),
    )


async def get_all_corridors_scored(
    session: AsyncSession,
    window_start: DateType | None = None,
    window_end: DateType | None = None,
) -> list[CorridorRead]:
    """Return all corridors with live-scored risk for the given date window (CR-007).

    Used when the list endpoint receives date params — runs the full scoring
    pipeline for every corridor so the map heat map reflects the chosen window.
    Falls back to get_all_corridors (stored risk) when no window is provided.
    """
    from services.corridor_risk import score_corridor

    rows = (
        await session.execute(select(CorridorRow).order_by(CorridorRow.name))
    ).scalars().all()

    result: list[CorridorRead] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for row in rows:
        risk_score, risk_level, risk_factors, works = await score_corridor(
            session, row.id, window_start=window_start, window_end=window_end
        )
        active_count = sum(1 for w in works if w.status == "in_progress")
        planned_count = sum(1 for w in works if w.status in ("submitted", "granted"))
        coords = _wkb_to_linestring(row.geometry)
        classification: RoadClassification = row.road_classification  # type: ignore[assignment]
        result.append(CorridorRead(
            id=row.id,
            name=row.name,
            road_classification=classification,
            geometry=LineStringGeometry(type="LineString", coordinates=coords),
            source=row.source,
            risk_level=risk_level,
            risk_score=risk_score,
            risk_factors=risk_factors,
            concurrent_works=works,
            active_works_count=active_count,
            planned_works_count=planned_count,
            last_calculated=now_iso,
        ))

    return result
