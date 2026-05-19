"""UN-006 — Composite Risk Scorer (Surface + Underground).

Combines the surface disruption score (CR-003, 60%) with the underground
asset density score (UN-002, 40%) into a single 0-100 composite risk score.

Weighting rationale:
  Surface (60%) — direct traffic and network disruption; primary operational
                  concern for highway authority officers.
  Underground (40%) — physical danger to buried infrastructure; serious but
                      secondary unless work involves excavation.

Formula: composite = (surface_score × 0.60) + (underground_score × 0.40)

The same four-level thresholds as CR-004 are applied to the composite score:
  0–24.9 → low | 25–49.9 → medium | 50–74.9 → high | 75–100 → critical

When no underground assets exist within 100 m of a corridor, the underground
score is 0 (not an error) and the composite naturally reduces to 60% of
the surface score — correctly reflecting a lower overall risk.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.domain import RiskLevel
from services.corridor_risk import classify_risk_level, score_corridor
from services.nuar_density import calculate_asset_density

logger = logging.getLogger(__name__)

# ── Weights — must sum to 1.0 ─────────────────────────────────────────────────

SURFACE_WEIGHT: float = 0.60
UNDERGROUND_WEIGHT: float = 0.40


# ── Result schema ─────────────────────────────────────────────────────────────

class CompositeRiskResult(BaseModel):
    """UN-006 composite risk output for one corridor."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    corridor_id: str
    surface_score: float          # 0–100 from CR-003
    surface_level: RiskLevel
    underground_score: float      # 0–100 from UN-002 (0 if no assets in range)
    underground_level: RiskLevel
    composite_score: float        # 0–100 weighted combination
    composite_level: RiskLevel
    surface_weight: float         # 0.60
    underground_weight: float     # 0.40
    underground_assets_in_range: int   # total assets within 100 m (0 = no data yet)
    calculated_at: str            # ISO 8601


# ── Scorer ────────────────────────────────────────────────────────────────────

async def compute_composite_risk(
    session: AsyncSession,
    corridor_id: str,
) -> CompositeRiskResult | None:
    """UN-006: Fetch both scores and combine them.

    Returns None if the corridor does not exist.
    Returns a valid result with underground_score=0 if no NUAR assets have
    been seeded or fall within the 100 m buffer.
    """
    # CR-003 surface score
    surface_score, surface_level, _factors, _works = await score_corridor(
        session, corridor_id
    )

    # UN-002 underground density (None only if corridor doesn't exist)
    density = await calculate_asset_density(session, corridor_id)
    if density is None:
        # corridor not found
        return None

    underground_score = density.density_score
    underground_level = density.density_level
    assets_in_range = density.total_assets

    composite = round(
        surface_score * SURFACE_WEIGHT + underground_score * UNDERGROUND_WEIGHT,
        2,
    )
    composite_level = classify_risk_level(composite)

    logger.info(
        "UN-006: corridor=%s surface=%.1f underground=%.1f composite=%.1f (%s)",
        corridor_id, surface_score, underground_score, composite, composite_level,
    )

    return CompositeRiskResult(
        corridor_id=corridor_id,
        surface_score=round(surface_score, 1),
        surface_level=surface_level,
        underground_score=round(underground_score, 1),
        underground_level=underground_level,
        composite_score=composite,
        composite_level=composite_level,
        surface_weight=SURFACE_WEIGHT,
        underground_weight=UNDERGROUND_WEIGHT,
        underground_assets_in_range=assets_in_range,
        calculated_at=datetime.now(timezone.utc).isoformat(),
    )
