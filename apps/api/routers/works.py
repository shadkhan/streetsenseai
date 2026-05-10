"""SM-006 — Street Manager data query endpoints.

Exposes the works stored in PostgreSQL/PostGIS for map queries, the
AI copilot layer, and Phase 2 corridor scoring. All responses are
camelCase JSON matching the TypeScript StreetWork interface.

Endpoints:
  GET /works/permit/{permit_reference}   single permit lookup
  GET /works/bbox                        spatial bounding-box query
  GET /works/usrn/{usrn}                all works on a USRN (street)
  GET /works/authority/{authority}       all works managed by an authority

Route ordering matters: specific paths (/bbox, /usrn, /authority) must
be declared before the catch-all path parameter (/permit/{ref:path}).
"""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.domain import StreetWork
from services.works_repository import (
    get_work_by_permit,
    get_works_by_authority,
    get_works_by_bbox,
    get_works_by_usrn,
)

router = APIRouter(prefix="/works", tags=["works"])

_DEFAULT_LIMIT = 100
_MAX_LIMIT = 500


@router.get(
    "/bbox",
    response_model=list[StreetWork],
    response_model_by_alias=True,
    summary="Spatial bounding-box query",
    description=(
        "Returns all works whose geometry intersects the given WGS-84 bounding box. "
        "Optionally filter by permit status and/or a proposed-date range. "
        "Date overlap test: proposed_start <= to_date AND proposed_end >= from_date."
    ),
)
async def get_by_bbox(
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    status: Annotated[list[str] | None, Query(description="One or more permit statuses")] = None,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: Annotated[int, Query(ge=1, le=_MAX_LIMIT, description="Max results")] = _DEFAULT_LIMIT,
    session: AsyncSession = Depends(get_db),
) -> list[StreetWork]:
    return await get_works_by_bbox(
        session,
        bbox=(min_lon, min_lat, max_lon, max_lat),
        statuses=status,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
    )


@router.get(
    "/usrn/{usrn}",
    response_model=list[StreetWork],
    response_model_by_alias=True,
    summary="All works on a specific street (USRN)",
)
async def get_by_usrn(
    usrn: str,
    status: Annotated[list[str] | None, Query(description="One or more permit statuses")] = None,
    session: AsyncSession = Depends(get_db),
) -> list[StreetWork]:
    return await get_works_by_usrn(session, usrn, statuses=status)


@router.get(
    "/authority/{authority}",
    response_model=list[StreetWork],
    response_model_by_alias=True,
    summary="All works managed by a highway authority",
)
async def get_by_authority(
    authority: str,
    status: Annotated[list[str] | None, Query(description="One or more permit statuses")] = None,
    session: AsyncSession = Depends(get_db),
) -> list[StreetWork]:
    return await get_works_by_authority(session, authority, statuses=status)


@router.get(
    "/permit/{permit_reference:path}",
    response_model=StreetWork,
    response_model_by_alias=True,
    summary="Get a single permit by reference",
    description=(
        "Permit references contain forward slashes (e.g. WG7/2025/04001234). "
        "The :path suffix captures slashes as part of the parameter value."
    ),
)
async def get_permit(
    permit_reference: str,
    session: AsyncSession = Depends(get_db),
) -> StreetWork:
    work = await get_work_by_permit(session, permit_reference)
    if work is None:
        raise HTTPException(status_code=404, detail=f"Permit '{permit_reference}' not found")
    return work
