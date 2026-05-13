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

from fastapi import APIRouter, Depends, HTTPException

from database import get_db
from schemas.corridor import CorridorRead
from services.corridor_repository import (
    get_all_corridors,
    get_corridor_by_id,
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
    "/",
    response_model=list[CorridorRead],
    response_model_by_alias=True,
    summary="List all corridors",
)
async def list_corridors(
    session: AsyncSession = Depends(get_db),
) -> list[CorridorRead]:
    return await get_all_corridors(session)


@router.get(
    "/{corridor_id}",
    response_model=CorridorRead,
    response_model_by_alias=True,
    summary="Get a single corridor by ID",
)
async def get_corridor(
    corridor_id: str,
    session: AsyncSession = Depends(get_db),
) -> CorridorRead:
    corridor = await get_corridor_by_id(session, corridor_id)
    if corridor is None:
        raise HTTPException(status_code=404, detail=f"Corridor '{corridor_id}' not found")
    return corridor
