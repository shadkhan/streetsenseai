"""UN-003 — Strike Risk Classifier.

For a given permit reference, queries NUAR underground assets within a
25 m buffer of the works geometry and classifies the overall excavation
strike risk as low / medium / high / critical.

Design:
  Buffer (25 m): wider than an excavation footprint but covers the
  "adjacent utilities zone" that contractors must be aware of.  Calibrated
  to produce meaningful hits with synthetic data (assets are generated
  within ~15 m of corridor centrelines; works are near the same centrelines).

  Risk scoring: presence-based with a count multiplier.  Gas (highest
  explosion risk) anchors the scale at 60; a single gas asset already
  puts a permit in "high" risk territory.  Multiple types or counts push
  toward "critical".

  Caching: a fresh DB record is inserted on each compute call.  Callers
  that want cached results should call nuar_repository.get_latest_strike_risk
  first and skip compute if the record is less than CACHE_SECONDS old.

  ADR-007 compliance: only the derived score is persisted (nuar_strike_risks).
  No asset geometry is written to the database.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from geoalchemy2.types import Geography
from models.nuar import NUARAsset, NUARAssetOwner, NUARAssetType
from models.street_work import StreetWork as StreetWorkRow
from schemas.nuar import HighestRiskAsset, StrikeRiskCreate, StrikeRiskRead
from services.nuar_repository import get_latest_strike_risk, save_strike_risk

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

# 25 m "adjacent utilities zone" — engineers check what's within 25 m of site
STRIKE_BUFFER_METRES: float = 25.0

# Seconds before a cached result is considered stale
CACHE_SECONDS: int = 300  # 5 minutes

# Base risk score for the PRESENCE of each utility type near an excavation.
# A single gas asset pushes the permit into "high" territory (score 60).
_TYPE_RISK_BASE: dict[str, float] = {
    "gas":      60.0,   # explosion / fire — highest excavation hazard
    "electric": 50.0,   # electrocution / power outage
    "water":    25.0,   # pressure damage / flooding
    "telecoms": 10.0,   # service disruption — low physical danger
    "other":     8.0,   # drainage, sewer
}

# Each additional asset of the highest-risk type adds this many points
_COUNT_BONUS_PER_ASSET: float = 2.5
_COUNT_BONUS_CAP: float = 20.0       # max bonus from count alone

# Each secondary type contributes its base × this fraction
_DIVERSITY_FACTOR: float = 0.15


# ── Scoring helpers (exported for unit tests) ─────────────────────────────────

def compute_strike_score(assets_by_type: dict[str, int]) -> float:
    """Return a 0-100 strike risk score for the given asset-type counts.

    Formula:
      base_score      = _TYPE_RISK_BASE of highest-risk type present
      count_bonus     = min((count_of_highest_type - 1) × 2.5, 20)
      diversity_bonus = sum of (base × 0.15) for every secondary type

    Returns 0.0 when no assets are found (no data → no risk assessed).
    """
    if not assets_by_type:
        return 0.0

    sorted_types = sorted(
        assets_by_type.keys(),
        key=lambda t: _TYPE_RISK_BASE.get(t, 5.0),
        reverse=True,
    )
    highest_type = sorted_types[0]

    base = _TYPE_RISK_BASE.get(highest_type, 5.0)
    count_bonus = min(
        (assets_by_type[highest_type] - 1) * _COUNT_BONUS_PER_ASSET,
        _COUNT_BONUS_CAP,
    )
    diversity_bonus = sum(
        _TYPE_RISK_BASE.get(t, 5.0) * _DIVERSITY_FACTOR
        for t in sorted_types[1:]
    )

    return min(round(base + count_bonus + diversity_bonus, 2), 100.0)


def classify_strike_level(score: float) -> str:
    """Same thresholds as CR-004 / UN-002 for UI consistency."""
    if score < 25.0:
        return "low"
    if score < 50.0:
        return "medium"
    if score < 75.0:
        return "high"
    return "critical"


def identify_highest_risk_asset(
    type_counts: dict[str, int],
    type_to_operator: dict[str, str],
) -> HighestRiskAsset | None:
    """Return metadata for the single highest-risk asset type found."""
    if not type_counts:
        return None
    highest_type = max(type_counts, key=lambda t: _TYPE_RISK_BASE.get(t, 5.0))
    solo_score = compute_strike_score({highest_type: type_counts[highest_type]})
    return HighestRiskAsset(
        type=highest_type,
        operator=type_to_operator.get(highest_type, "Unknown"),
        risk=classify_strike_level(solo_score),
    )


# ── Main service function ─────────────────────────────────────────────────────

async def compute_strike_risk(
    session: AsyncSession,
    permit_reference: str,
) -> StrikeRiskRead | None:
    """UN-003: Classify excavation strike risk for a permit.

    Returns None if the permit reference does not exist in street_works.

    Cache behaviour: if a record already exists for this permit that is
    less than CACHE_SECONDS old, the cached result is returned without
    rerunning the spatial query.  Otherwise a fresh result is computed,
    inserted into nuar_strike_risks, and returned.
    """
    # ── 1. Cache check ────────────────────────────────────────────────────────
    cached = await get_latest_strike_risk(session, permit_reference)
    if cached is not None:
        age = datetime.now(timezone.utc) - cached.calculated_at.replace(tzinfo=timezone.utc)
        if age.total_seconds() < CACHE_SECONDS:
            logger.debug("UN-003: cache hit for permit %s (age %.0fs)", permit_reference, age.total_seconds())
            return cached

    # ── 2. Verify permit exists ───────────────────────────────────────────────
    work_exists = await session.scalar(
        select(func.count())
        .select_from(StreetWorkRow)
        .where(StreetWorkRow.permit_reference == permit_reference)
    )
    if not work_exists:
        return None

    # ── 3. Spatial join: NUAR assets within STRIKE_BUFFER_METRES of permit ────
    work_geom_sub = (
        select(StreetWorkRow.geometry)
        .where(StreetWorkRow.permit_reference == permit_reference)
        .scalar_subquery()
    )

    stmt = (
        select(
            NUARAssetOwner.asset_type,
            NUARAssetOwner.name.label("operator_name"),
            func.count().label("cnt"),
        )
        .select_from(NUARAsset)
        .join(NUARAssetType, NUARAsset.asset_type_id == NUARAssetType.id)
        .join(NUARAssetOwner, NUARAssetType.owner_id == NUARAssetOwner.id)
        .where(
            func.ST_DWithin(
                cast(NUARAsset.geometry, Geography()),
                cast(work_geom_sub, Geography()),
                STRIKE_BUFFER_METRES,
            )
        )
        .group_by(NUARAssetOwner.asset_type, NUARAssetOwner.name)
        .order_by(func.count().desc())
    )

    rows = (await session.execute(stmt)).all()

    # Aggregate: multiple operators can share a type (e.g. BT + VMO2 → "telecoms")
    assets_by_type: dict[str, int] = {}
    # For each type, keep the operator with the most assets
    type_to_operator: dict[str, str] = {}
    type_best_count: dict[str, int] = {}

    for row in rows:
        asset_type: str = row.asset_type
        cnt: int = row.cnt
        operator: str = row.operator_name

        assets_by_type[asset_type] = assets_by_type.get(asset_type, 0) + cnt

        if cnt > type_best_count.get(asset_type, 0):
            type_to_operator[asset_type] = operator
            type_best_count[asset_type] = cnt

    # ── 4. Score + classify ───────────────────────────────────────────────────
    score = compute_strike_score(assets_by_type)
    level = classify_strike_level(score)
    total = sum(assets_by_type.values())
    highest = identify_highest_risk_asset(assets_by_type, type_to_operator)

    logger.info(
        "UN-003: permit=%s total=%d score=%.1f level=%s buffer=%.0fm",
        permit_reference, total, score, level, STRIKE_BUFFER_METRES,
    )

    # ── 5. Persist (ADR-007: score only, no geometry) ─────────────────────────
    data = StrikeRiskCreate(
        permit_reference=permit_reference,
        overall_risk=level,
        asset_count=total,
        assets_by_type=assets_by_type,
        highest_risk_asset=highest,
    )
    row_saved = await save_strike_risk(session, data)
    await session.commit()

    return StrikeRiskRead(
        id=row_saved.id,
        permit_reference=permit_reference,
        overall_risk=level,
        asset_count=total,
        assets_by_type=assets_by_type,
        highest_risk_asset=highest,
        calculated_at=row_saved.calculated_at,
    )
