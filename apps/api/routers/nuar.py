"""NUAR underground asset endpoints — Phase 4 (UN-001 through UN-007).

Currently wired for UN-008 (synthetic seed) and stub endpoints.
Live NUAR API integration (UN-001) and scoring modules (UN-002 to UN-007)
will be added incrementally as Phase 4 progresses.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.nuar import NUARAsset, NUARAssetOwner, NUARAssetType
from services.nuar_synthetic import generate_nuar_assets

router = APIRouter(prefix="/nuar", tags=["nuar"])


# ── UN-008: Synthetic seed ────────────────────────────────────────────────────

@router.post(
    "/admin/seed",
    status_code=200,
    summary="UN-008 — Seed synthetic NUAR underground assets",
    description=(
        "Generates ~405 deterministic synthetic underground assets across "
        "5 Birmingham corridors following the NUAR Harmonised Data Model. "
        "Idempotent — safe to call multiple times. "
        "ADR-007: data_source='synthetic' on every record."
    ),
)
async def seed_nuar_assets(
    session: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    return await generate_nuar_assets(session)  # type: ignore[return-value]


# ── Admin stats ────────────────────────────────────────────────────────────────

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
