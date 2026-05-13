"""AI-005 — Scheduling Advisor: detect overlapping permit schedules on corridors.

For each corridor, finds pairs of concurrent works whose proposed date ranges
overlap.  Scores the severity of each pair using the same traffic-management
weights as the corridor risk engine plus an overlap-duration factor.
Returns conflicts sorted by severity_score descending.
"""
from __future__ import annotations

import logging
from datetime import date as DateType

from sqlalchemy.ext.asyncio import AsyncSession

from schemas.scheduling import SchedulingConflict
from services.corridor_repository import get_all_corridors
from services.corridor_risk import (
    _TRAFFIC_MGMT_SCORES,
    classify_risk_level,
    get_works_near_corridor,
)

logger = logging.getLogger(__name__)

_STATUS_PRIORITY: dict[str, int] = {
    "in_progress": 3,
    "granted": 2,
    "submitted": 1,
}


async def find_scheduling_conflicts(
    session: AsyncSession,
    window_start: DateType | None = None,
    window_end: DateType | None = None,
    corridor_id: str | None = None,
) -> list[SchedulingConflict]:
    """AI-005: Detect scheduling conflicts across corridors.

    For each corridor, examines all pairs of near-by works and flags those
    whose proposed_start_date / proposed_end_date ranges overlap.

    Severity formula:
        severity_score = (tmgt_score_a + tmgt_score_b) / 2 * duration_factor
        duration_factor = min(overlap_days / 7, 2.0)   # caps at 2× for 14+ days

    Recommendation: the work with lower status priority is flagged for deferral
    (in_progress > granted > submitted).

    corridor_id: if provided, restricts the scan to that corridor only.
    window_start/window_end: date filter forwarded to get_works_near_corridor.
    """
    corridors = await get_all_corridors(session)
    if corridor_id is not None:
        corridors = [c for c in corridors if c.id == corridor_id]

    conflicts: list[SchedulingConflict] = []
    seen_pairs: set[frozenset[str]] = set()

    for corridor in corridors:
        works = await get_works_near_corridor(
            session, corridor.id, window_start=window_start, window_end=window_end
        )
        if len(works) < 2:
            continue

        for i, work_a in enumerate(works):
            for work_b in works[i + 1 :]:
                pair = frozenset({work_a.permit_reference, work_b.permit_reference})
                if pair in seen_pairs:
                    continue

                try:
                    start_a = DateType.fromisoformat(work_a.proposed_start_date)
                    end_a = DateType.fromisoformat(work_a.proposed_end_date)
                    start_b = DateType.fromisoformat(work_b.proposed_start_date)
                    end_b = DateType.fromisoformat(work_b.proposed_end_date)
                except ValueError:
                    continue

                overlap_start = max(start_a, start_b)
                overlap_end = min(end_a, end_b)
                if overlap_start > overlap_end:
                    continue

                seen_pairs.add(pair)
                overlap_days = (overlap_end - overlap_start).days + 1

                score_a = _TRAFFIC_MGMT_SCORES.get(
                    work_a.traffic_management_type.lower().replace(" ", "_"), 0.0
                )
                score_b = _TRAFFIC_MGMT_SCORES.get(
                    work_b.traffic_management_type.lower().replace(" ", "_"), 0.0
                )
                duration_factor = min(overlap_days / 7.0, 2.0)
                severity_score = min((score_a + score_b) / 2.0 * duration_factor, 100.0)
                severity = classify_risk_level(severity_score)

                priority_a = _STATUS_PRIORITY.get(work_a.status, 0)
                priority_b = _STATUS_PRIORITY.get(work_b.status, 0)
                if priority_a >= priority_b:
                    defer_ref = work_b.permit_reference
                    defer_promoter = work_b.promoter
                else:
                    defer_ref = work_a.permit_reference
                    defer_promoter = work_a.promoter

                recommendation = (
                    f"Consider deferring {defer_ref} ({defer_promoter}) "
                    f"by {overlap_days} day(s) to eliminate the overlap."
                )

                conflicts.append(
                    SchedulingConflict(
                        corridor_id=corridor.id,
                        corridor_name=corridor.name,
                        permit_a=work_a.permit_reference,
                        permit_b=work_b.permit_reference,
                        street_name=work_a.street_name,
                        overlap_start=overlap_start.isoformat(),
                        overlap_end=overlap_end.isoformat(),
                        overlap_days=overlap_days,
                        severity=severity,
                        severity_score=round(severity_score, 1),
                        promoter_a=work_a.promoter,
                        promoter_b=work_b.promoter,
                        traffic_management_a=work_a.traffic_management_type,
                        traffic_management_b=work_b.traffic_management_type,
                        recommendation=recommendation,
                    )
                )

    conflicts.sort(key=lambda c: c.severity_score, reverse=True)
    logger.info("AI-005: found %d scheduling conflicts", len(conflicts))
    return conflicts
