"""NUAR underground asset endpoints — Phase 4 (UN-001 through UN-007).

Endpoints:
  POST /nuar/admin/seed                              UN-008 — synthetic seed
  GET  /nuar/admin/stats                             UN-008 — record counts
  GET  /nuar/corridors/{id}/density                  UN-002 — asset density scorer
  GET  /nuar/permits/{permit_reference:path}/strike-risk   UN-003 — strike risk
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.nuar import NUARAsset, NUARAssetOwner, NUARAssetType
from schemas.nuar import StrikeRiskRead
from services.nuar_density import AssetDensityResult, calculate_asset_density
from services.nuar_strike import compute_strike_risk
from services.nuar_synthetic import generate_nuar_assets

router = APIRouter(prefix="/nuar", tags=["nuar"])


# ── UN-008: Synthetic seed ────────────────────────────────────────────────────

@router.post(
    "/admin/seed",
    status_code=200,
    summary="UN-008 — Seed synthetic NUAR underground assets",
    description=(
        "Generates ~395 deterministic synthetic underground assets across "
        "5 Birmingham corridors. Idempotent. ADR-007: data_source='synthetic'."
    ),
)
async def seed_nuar_assets(
    session: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    return await generate_nuar_assets(session)  # type: ignore[return-value]


@router.get(
    "/admin/stats",
    summary="UN-008 — Return synthetic asset counts",
)
async def get_nuar_stats(
    session: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    owner_count = await session.scalar(select(func.count()).select_from(NUARAssetOwner))
    type_count = await session.scalar(select(func.count()).select_from(NUARAssetType))
    asset_count = await session.scalar(
        select(func.count()).select_from(NUARAsset)
        .where(NUARAsset.data_source == "synthetic")
    )
    return {
        "owner_count": int(owner_count or 0),
        "type_count": int(type_count or 0),
        "synthetic_asset_count": int(asset_count or 0),
    }


# ── UN-002: Asset density scorer ──────────────────────────────────────────────

@router.get(
    "/corridors/{corridor_id}/density",
    response_model=AssetDensityResult,
    response_model_by_alias=True,
    summary="UN-002 — Underground asset density for a corridor",
    description=(
        "Counts NUAR underground assets within 100 m of the corridor geometry, "
        "grouped by utility type, with a weighted 0-100 density score."
    ),
)
async def get_corridor_density(
    corridor_id: str,
    session: AsyncSession = Depends(get_db),
) -> AssetDensityResult:
    result = await calculate_asset_density(session, corridor_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Corridor '{corridor_id}' not found")
    return result


# ── UN-003: Strike risk classifier ────────────────────────────────────────────

@router.get(
    "/permits/{permit_reference:path}/strike-risk",
    response_model=StrikeRiskRead,
    response_model_by_alias=True,
    summary="UN-003 — Excavation strike risk for a permit",
    description=(
        "Queries NUAR underground assets within 25 m of the permit works geometry "
        "and returns a strike risk classification (low/medium/high/critical). "
        "Result is cached for 5 minutes. Requires UN-008 seed data."
    ),
)
async def get_permit_strike_risk(
    permit_reference: str,
    session: AsyncSession = Depends(get_db),
) -> StrikeRiskRead:
    result = await compute_strike_risk(session, permit_reference)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Permit '{permit_reference}' not found in Street Manager data",
        )
    return result
