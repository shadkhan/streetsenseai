"""UN-002 — Asset Density Scorer.

Queries nuar_underground_assets within 100 m of a corridor's LineString
geometry using PostGIS ST_DWithin (geography, metres).  Groups results by
utility type (gas / electric / water / telecoms / other) and applies
risk-weighted scoring to produce a 0-100 density score.

Design:
  - No migration required — reads from tables created by UN-001-prep.
  - Buffer distance matches CR-002 (100 m) for consistency.
  - Normaliser calibrated so a single fully loaded Birmingham corridor
    (all 6 utility types, ~79 synthetic assets) scores ~61 ("high").
    A corridor at the junction of two or more adjacent corridors that
    share overlapping 100 m buffers can reach "critical" (>75).
  - Returns AssetDensityResult for route handler; scoring helpers are
    exported so tests can exercise them directly without a DB.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from geoalchemy2.types import Geography
from models.corridor import Corridor as CorridorRow
from models.nuar import NUARAsset, NUARAssetOwner, NUARAssetType
from schemas.domain import RiskLevel

logger = logging.getLogger(__name__)

# ── Scoring constants ─────────────────────────────────────────────────────────

# Risk weights per utility type — reflects physical danger if struck
_ASSET_TYPE_WEIGHTS: dict[str, float] = {
    "gas":      2.0,   # explosion / fire risk
    "electric": 1.8,   # electrocution risk
    "water":    1.2,   # pressure damage / flooding
    "telecoms": 0.8,   # service disruption — lower physical risk
    "other":    1.0,   # drainage, sewer
}

CORRIDOR_BUFFER_METRES: float = 100.0

# Weighted units at which the density score reaches 100 (critical).
# Calibrated: single Birmingham corridor (weighted_sum ≈ 122) → ~61 "high".
# Two adjacent overlapping corridors (weighted_sum ≈ 244) → capped at 100.
_DENSITY_NORMALISER: float = 200.0


# ── Domain result model ───────────────────────────────────────────────────────

class AssetDensityResult(BaseModel):
    """UN-002 output — asset density for one corridor.

    Mirrors the TypeScript AssetDensity interface in apps/web/types/index.ts.
    Uses camelCase aliases for direct JSON serialisation.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    corridor_id: str
    total_assets: int
    assets_by_type: dict[str, int]        # {"gas": 23, "electric": 21, ...}
    weighted_score: float                  # pre-normalised weighted sum (for debug)
    density_score: float                   # 0–100
    density_level: RiskLevel
    calculated_at: str                     # ISO 8601


# ── Scoring helpers (exported for tests) ─────────────────────────────────────

def compute_weighted_sum(assets_by_type: dict[str, int]) -> float:
    """Return the sum of (count × type_weight) for each utility type."""
    return sum(
        count * _ASSET_TYPE_WEIGHTS.get(asset_type, 1.0)
        for asset_type, count in assets_by_type.items()
    )


def compute_density_score(weighted_sum: float) -> float:
    """Normalise a weighted sum to 0–100, capped at 100."""
    return min(round(weighted_sum / _DENSITY_NORMALISER * 100, 2), 100.0)


def classify_density_level(score: float) -> RiskLevel:
    """Re-use the same thresholds as corridor risk (CR-004):
    0–24.9 → low | 25–49.9 → medium | 50–74.9 → high | 75–100 → critical
    """
    if score < 25.0:
        return "low"
    if score < 50.0:
        return "medium"
    if score < 75.0:
        return "high"
    return "critical"


# ── Main scorer ───────────────────────────────────────────────────────────────

async def calculate_asset_density(
    session: AsyncSession,
    corridor_id: str,
    buffer_metres: float = CORRIDOR_BUFFER_METRES,
) -> AssetDensityResult | None:
    """UN-002: Return asset density for a corridor.

    Returns None if the corridor ID does not exist.
    Returns a zero-score result (density_level='low') if no assets fall
    within buffer_metres — e.g. before UN-008 seed has been run.
    """
    corridor_geom_sub = (
        select(CorridorRow.geometry)
        .where(CorridorRow.id == corridor_id)
        .scalar_subquery()
    )

    # Check corridor exists first — scalar_subquery would silently return NULL
    corridor_exists = await session.scalar(
        select(func.count()).select_from(CorridorRow).where(CorridorRow.id == corridor_id)
    )
    if not corridor_exists:
        return None

    # Spatial join: asset geometry within buffer of corridor LineString
    stmt = (
        select(NUARAssetOwner.asset_type, func.count().label("cnt"))
        .select_from(NUARAsset)
        .join(NUARAssetType, NUARAsset.asset_type_id == NUARAssetType.id)
        .join(NUARAssetOwner, NUARAssetType.owner_id == NUARAssetOwner.id)
        .where(
            func.ST_DWithin(
                cast(NUARAsset.geometry, Geography()),
                cast(corridor_geom_sub, Geography()),
                buffer_metres,
            )
        )
        .group_by(NUARAssetOwner.asset_type)
    )

    rows = (await session.execute(stmt)).all()
    assets_by_type: dict[str, int] = {row.asset_type: row.cnt for row in rows}
    total = sum(assets_by_type.values())

    weighted = compute_weighted_sum(assets_by_type)
    score = compute_density_score(weighted)
    level = classify_density_level(score)

    logger.info(
        "UN-002: corridor=%s total=%d weighted=%.1f score=%.1f level=%s",
        corridor_id, total, weighted, score, level,
    )

    return AssetDensityResult(
        corridor_id=corridor_id,
        total_assets=total,
        assets_by_type=assets_by_type,
        weighted_score=round(weighted, 2),
        density_score=score,
        density_level=level,
        calculated_at=datetime.now(timezone.utc).isoformat(),
    )
