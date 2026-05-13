"""CR-002 / CR-003 / CR-004 — Corridor risk scoring engine.

CR-002  get_works_near_corridor  — PostGIS ST_DWithin spatial join: finds all
        active/planned street works whose geometry falls within 100 m of a
        corridor's LineString geometry.

CR-003  compute_risk_score       — Weighted 0-100 score from four factors:
        concurrent works count, traffic management severity, work type, and
        road classification.  Returns the score plus a RiskFactor list.

CR-004  classify_risk_level      — Maps 0-100 score to the four-level enum
        (low / medium / high / critical).

score_corridor                   — Orchestrates CR-002 + CR-003 + CR-004 for
        a single corridor ID, returning the full risk picture.
"""
from __future__ import annotations

import logging
from datetime import date as DateType

from sqlalchemy import cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from geoalchemy2.types import Geography
from models.corridor import Corridor as CorridorRow
from models.street_work import StreetWork as StreetWorkRow
from schemas.domain import RiskFactor, RiskLevel, StreetWork
from services.works_repository import _row_to_domain as _work_row_to_domain

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

CORRIDOR_BUFFER_METRES: float = 100.0

# Works in these statuses are considered when computing risk
_ACTIVE_STATUSES = ("submitted", "granted", "in_progress")

# Traffic management severity — higher = more disruptive
_TRAFFIC_MGMT_SCORES: dict[str, float] = {
    "road_closure": 100.0,
    "convoy_working": 90.0,
    "contra_flow": 85.0,
    "one_way_alternating": 70.0,
    "lane_closure": 65.0,
    "multi_way_signals": 55.0,
    "two_way_signals": 45.0,
    "stop_and_go_boards": 45.0,
    "give_and_take": 25.0,
    "some_incursion": 10.0,
    "no_traffic_management": 5.0,
}

# Work type severity — higher = more disruptive
_WORK_TYPE_SCORES: dict[str, float] = {
    "major": 100.0,
    "immediate": 85.0,
    "standard": 60.0,
    "minor": 25.0,
}

# Road classification importance — A roads carry the most traffic
_ROAD_CLASS_SCORES: dict[str, float] = {
    "A": 100.0,
    "B": 65.0,
    "C": 35.0,
    "unclassified": 15.0,
}

# Factor weights — must sum to 1.0
_W_COUNT = 0.40
_W_TRAFFIC = 0.30
_W_WORK_TYPE = 0.20
_W_ROAD_CLASS = 0.10


# ── CR-004: Risk classification ────────────────────────────────────────────────

def classify_risk_level(score: float) -> RiskLevel:
    """CR-004: Map a 0-100 risk score to a four-level risk label.

    Thresholds:  0–24.9 → low | 25–49.9 → medium | 50–74.9 → high | 75–100 → critical
    """
    if score < 25.0:
        return "low"
    if score < 50.0:
        return "medium"
    if score < 75.0:
        return "high"
    return "critical"


# ── CR-003: Risk scoring ───────────────────────────────────────────────────────

def compute_risk_score(
    works: list[StreetWork],
    road_classification: str,
) -> tuple[float, list[RiskFactor]]:
    """CR-003: Compute a 0-100 risk score and contributing RiskFactor list.

    Four weighted factors:
      concurrent_works   (40%) — number of active/planned works near corridor
      traffic_management (30%) — highest-severity traffic management type present
      work_type          (20%) — highest-severity work category present
      road_classification(10%) — importance of the road (A > B > C > unclassified)

    Returns (score, factors). Returns (0.0, []) when there are no works.
    """
    if not works:
        return 0.0, []

    factors: list[RiskFactor] = []

    # ── Factor 1: Concurrent works count (0-100, caps at 4+ works) ────────────
    count = len(works)
    count_raw = min(count * 25.0, 100.0)
    count_contribution = round(count_raw * _W_COUNT, 2)
    factors.append(
        RiskFactor(
            factor="concurrent_works",
            weight=_W_COUNT,
            contribution=count_contribution,
            description=f"{count} concurrent {'work' if count == 1 else 'works'} on corridor",
        )
    )

    # ── Factor 2: Highest traffic management severity ─────────────────────────
    traffic_raw = max(
        (
            _TRAFFIC_MGMT_SCORES.get(w.traffic_management_type.lower().replace(" ", "_"), 0.0)
            for w in works
        ),
        default=0.0,
    )
    traffic_contribution = round(traffic_raw * _W_TRAFFIC, 2)
    worst_traffic = max(
        works,
        key=lambda w: _TRAFFIC_MGMT_SCORES.get(
            w.traffic_management_type.lower().replace(" ", "_"), 0.0
        ),
    )
    factors.append(
        RiskFactor(
            factor="traffic_management",
            weight=_W_TRAFFIC,
            contribution=traffic_contribution,
            description=(
                f"Highest severity: '{worst_traffic.traffic_management_type}' "
                f"(permit {worst_traffic.permit_reference})"
            ),
        )
    )

    # ── Factor 3: Highest work type severity ──────────────────────────────────
    work_type_raw = max(
        (
            _WORK_TYPE_SCORES.get(w.work_type.lower(), 0.0)
            for w in works
        ),
        default=0.0,
    )
    work_type_contribution = round(work_type_raw * _W_WORK_TYPE, 2)
    worst_type = max(
        works,
        key=lambda w: _WORK_TYPE_SCORES.get(w.work_type.lower(), 0.0),
    )
    factors.append(
        RiskFactor(
            factor="work_type",
            weight=_W_WORK_TYPE,
            contribution=work_type_contribution,
            description=(
                f"Highest severity: '{worst_type.work_type}' work "
                f"(permit {worst_type.permit_reference})"
            ),
        )
    )

    # ── Factor 4: Road classification importance ──────────────────────────────
    class_raw = _ROAD_CLASS_SCORES.get(road_classification, 15.0)
    class_contribution = round(class_raw * _W_ROAD_CLASS, 2)
    factors.append(
        RiskFactor(
            factor="road_classification",
            weight=_W_ROAD_CLASS,
            contribution=class_contribution,
            description=f"{road_classification.upper()} road — elevated traffic volume",
        )
    )

    score = min(sum(f.contribution for f in factors), 100.0)
    logger.debug(
        "Corridor risk: count=%d traffic_raw=%.0f type_raw=%.0f class_raw=%.0f → %.1f",
        count, traffic_raw, work_type_raw, class_raw, score,
    )
    return round(score, 2), factors


# ── CR-002: Spatial join ───────────────────────────────────────────────────────

async def get_works_near_corridor(
    session: AsyncSession,
    corridor_id: str,
    buffer_metres: float = CORRIDOR_BUFFER_METRES,
    window_start: DateType | None = None,
    window_end: DateType | None = None,
) -> list[StreetWork]:
    """CR-002: Find active/planned works within buffer_metres of the corridor.

    Uses PostGIS ST_DWithin with geography cast for metre-accurate distances.
    Only returns works in status: submitted, granted, in_progress.

    If window_start/window_end are provided, further filters to works whose
    date range overlaps with [window_start, window_end] using the interval
    overlap condition: work.start <= window_end AND work.end >= window_start.
    """
    corridor_geom_sub = (
        select(CorridorRow.geometry)
        .where(CorridorRow.id == corridor_id)
        .scalar_subquery()
    )

    from sqlalchemy import func
    stmt = (
        select(StreetWorkRow)
        .where(
            StreetWorkRow.status.in_(_ACTIVE_STATUSES),
            func.ST_DWithin(
                cast(StreetWorkRow.geometry, Geography()),
                cast(corridor_geom_sub, Geography()),
                buffer_metres,
            ),
        )
    )

    if window_start is not None:
        stmt = stmt.where(StreetWorkRow.proposed_end_date >= window_start)
    if window_end is not None:
        stmt = stmt.where(StreetWorkRow.proposed_start_date <= window_end)

    rows = (await session.execute(stmt)).scalars().all()
    works = [_work_row_to_domain(row) for row in rows]
    logger.debug(
        "CR-002: corridor %s — %d works within %.0fm (window %s–%s)",
        corridor_id, len(works), buffer_metres, window_start, window_end,
    )
    return works


# ── Orchestrator ───────────────────────────────────────────────────────────────

async def score_corridor(
    session: AsyncSession,
    corridor_id: str,
    window_start: DateType | None = None,
    window_end: DateType | None = None,
) -> tuple[float, RiskLevel, list[RiskFactor], list[StreetWork]]:
    """Run CR-002 + CR-003 + CR-004 for one corridor.

    Returns (risk_score, risk_level, risk_factors, concurrent_works).
    Returns zero-risk values if the corridor does not exist.
    window_start/window_end optionally restrict works to a date window (CR-007).
    """
    row = await session.get(CorridorRow, corridor_id)
    if row is None:
        logger.warning("score_corridor: corridor '%s' not found", corridor_id)
        return 0.0, "low", [], []

    works = await get_works_near_corridor(
        session, corridor_id, window_start=window_start, window_end=window_end
    )
    score, factors = compute_risk_score(works, row.road_classification)
    level = classify_risk_level(score)

    logger.info(
        "CR-003/004: corridor=%s works=%d score=%.1f level=%s (window %s–%s)",
        corridor_id, len(works), score, level, window_start, window_end,
    )
    return score, level, factors, works
