"""CR-001 — Corridor query endpoints.

Exposes the corridor definitions stored in PostgreSQL/PostGIS.
Risk scoring fields (riskLevel, riskScore, riskFactors) are populated
by CR-003/CR-004; they are null until those modules run.

Endpoints:
  GET /corridors/bbox          spatial bounding-box query
  GET /corridors               list all corridors
  GET /corridors/{id}          single corridor by slug ID

Route ordering: /bbox must come before /{id} to prevent "bbox" being
treated as a corridor ID.
"""
from __future__ import annotations

from datetime import date as DateType

from fastapi import APIRouter, Depends, HTTPException

from database import get_db
from schemas.corridor import CorridorRead
from services.corridor_repository import (
    get_all_corridors,
    get_all_corridors_scored,
    get_corridor_by_id,
    get_corridor_with_risk,
    get_corridors_by_bbox,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/corridors", tags=["corridors"])


@router.get(
    "/bbox",
    response_model=list[CorridorRead],
    response_model_by_alias=True,
    summary="Corridors intersecting a bounding box",
    description=(
        "Returns all corridor LineStrings that intersect the given WGS-84 bbox. "
        "Used by CR-005 to load visible corridors for the map canvas."
    ),
)
async def get_by_bbox(
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    session: AsyncSession = Depends(get_db),
) -> list[CorridorRead]:
    return await get_corridors_by_bbox(
        session, bbox=(min_lon, min_lat, max_lon, max_lat)
    )


@router.get(
    "",
    response_model=list[CorridorRead],
    response_model_by_alias=True,
    summary="List all corridors",
    description=(
        "Returns all corridors. Without date params, serves stored risk values. "
        "With start_date/end_date, runs live scoring restricted to that window (CR-007)."
    ),
)
async def list_corridors(
    start_date: DateType | None = None,
    end_date: DateType | None = None,
    session: AsyncSession = Depends(get_db),
) -> list[CorridorRead]:
    if start_date is not None or end_date is not None:
        return await get_all_corridors_scored(session, window_start=start_date, window_end=end_date)
    return await get_all_corridors(session)


@router.get(
    "/{corridor_id}",
    response_model=CorridorRead,
    response_model_by_alias=True,
    summary="Get a single corridor by ID",
    description=(
        "Returns full corridor detail including live-computed risk score, "
        "risk factors (CR-003), and concurrent works within 100 m of the "
        "corridor geometry (CR-002)."
    ),
)
async def get_corridor(
    corridor_id: str,
    start_date: DateType | None = None,
    end_date: DateType | None = None,
    session: AsyncSession = Depends(get_db),
) -> CorridorRead:
    corridor = await get_corridor_with_risk(
        session, corridor_id, window_start=start_date, window_end=end_date
    )
    if corridor is None:
        raise HTTPException(status_code=404, detail=f"Corridor '{corridor_id}' not found")
    return corridor
