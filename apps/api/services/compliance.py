"""NC-001 — Promoter Compliance Scorer.

Derives all compliance metrics from the existing street_works table.
No additional migration is required — all signals come from permit dates,
actual dates, and status fields already present in Phase 1 data.

Scoring formula (0–100, higher = better):
  base = 100
  - overrun penalty:              overrun_rate   × 40
  - late-start penalty:           late_start_rate × 30
  - missing-reinstatement penalty: missing_reinstatement_rate × 30

Trend: compare compliance score for the most-recent 6 months versus the
preceding 6 months.  > +5 → improving, < -5 → deteriorating, else stable.
"""
from __future__ import annotations

import csv
import io
import logging
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.street_work import StreetWork as StreetWorkRow
from schemas.compliance import (
    ComplianceSummary,
    FPNOpportunity,
    MonthlyTrend,
    PromoterComplianceRead,
)

logger = logging.getLogger(__name__)

# ── Internal helpers ──────────────────────────────────────────────────────────

def _score(
    works: list[StreetWorkRow],
    today: date,
) -> tuple[float, float, float, float]:
    """Return (compliance_score, overrun_rate, late_start_rate, missing_rate)."""
    if not works:
        return 100.0, 0.0, 0.0, 0.0

    completed = [w for w in works if w.actual_end_date is not None]
    overruns = sum(
        1 for w in completed if w.actual_end_date.date() > w.proposed_end_date
    )
    overrun_rate = overruns / len(completed) if completed else 0.0

    started = [w for w in works if w.actual_start_date is not None]
    late_starts = sum(
        1 for w in started if w.actual_start_date.date() > w.proposed_start_date
    )
    late_start_rate = late_starts / len(started) if started else 0.0

    missing = sum(
        1 for w in works
        if w.status == "in_progress" and w.proposed_end_date < today
    )
    missing_rate = missing / len(works)

    raw = 100.0 - (overrun_rate * 40.0) - (late_start_rate * 30.0) - (missing_rate * 30.0)
    score = max(0.0, min(100.0, raw))
    return score, overrun_rate, late_start_rate, missing_rate


def _trend(
    all_works: list[StreetWorkRow],
    today: date,
) -> Literal["improving", "stable", "deteriorating"]:
    """Compare score of last 6 months vs previous 6 months."""
    from datetime import timedelta
    six_ago = today - timedelta(days=182)
    twelve_ago = today - timedelta(days=365)

    recent = [w for w in all_works if w.proposed_start_date >= six_ago]
    prev = [
        w for w in all_works
        if twelve_ago <= w.proposed_start_date < six_ago
    ]

    recent_score, *_ = _score(recent, today)
    prev_score, *_ = _score(prev, today)

    if recent_score > prev_score + 5:
        return "improving"
    if recent_score < prev_score - 5:
        return "deteriorating"
    return "stable"


def _mode(values: list[str]) -> str:
    if not values:
        return "Unknown"
    return max(set(values), key=values.count)


# ── Public API ────────────────────────────────────────────────────────────────

async def compute_all_promoters(
    session: AsyncSession,
    today: date | None = None,
) -> list[PromoterComplianceRead]:
    """NC-001 — Compute compliance scores for every promoter in the dataset."""
    today = today or date.today()
    now_iso = datetime.now(timezone.utc).isoformat()

    rows: list[StreetWorkRow] = list(
        (await session.execute(select(StreetWorkRow))).scalars().all()
    )

    by_licence: dict[str, list[StreetWorkRow]] = defaultdict(list)
    for row in rows:
        key = row.promoter_licence_number or "UNKNOWN"
        by_licence[key].append(row)

    results: list[PromoterComplianceRead] = []
    for licence, works in by_licence.items():
        score, overrun_rate, late_start_rate, missing_rate = _score(works, today)
        results.append(
            PromoterComplianceRead(
                promoter_licence_number=licence,
                promoter_name=_mode([w.promoter for w in works if w.promoter]),
                total_works=len(works),
                overrun_rate=round(overrun_rate, 4),
                late_start_rate=round(late_start_rate, 4),
                missing_reinstatement_rate=round(missing_rate, 4),
                compliance_score=round(score, 1),
                trend=_trend(works, today),
                region=_mode([w.authority for w in works if w.authority]),
                last_updated=now_iso,
            )
        )

    return sorted(results, key=lambda r: r.compliance_score)


async def get_compliance_summary(
    session: AsyncSession,
) -> ComplianceSummary:
    """NC-002 — Dashboard summary stats."""
    promoters = await compute_all_promoters(session)
    fpn = await get_fpn_opportunities(session)
    now_iso = datetime.now(timezone.utc).isoformat()

    avg = sum(p.compliance_score for p in promoters) / len(promoters) if promoters else 0.0

    return ComplianceSummary(
        total_promoters=len(promoters),
        avg_compliance_score=round(avg, 1),
        worst_offender=promoters[0] if promoters else None,
        best_performer=promoters[-1] if promoters else None,
        total_fpn_opportunities=len(fpn),
        calculated_at=now_iso,
    )


async def get_fpn_opportunities(
    session: AsyncSession,
) -> list[FPNOpportunity]:
    """NC-005 — Works that overran: Fixed Penalty Notice candidates."""
    stmt = select(StreetWorkRow).where(
        StreetWorkRow.actual_end_date.is_not(None),
        StreetWorkRow.status.in_(["completed", "closed"]),
    )
    rows = (await session.execute(stmt)).scalars().all()

    results: list[FPNOpportunity] = []
    for row in rows:
        overrun_days = (row.actual_end_date.date() - row.proposed_end_date).days
        if overrun_days >= 1:
            results.append(
                FPNOpportunity(
                    permit_reference=row.permit_reference,
                    promoter=row.promoter,
                    promoter_licence_number=row.promoter_licence_number,
                    street_name=row.street_name,
                    authority=row.authority,
                    proposed_end_date=str(row.proposed_end_date),
                    actual_end_date=str(row.actual_end_date.date()),
                    overrun_days=overrun_days,
                )
            )

    return sorted(results, key=lambda r: r.overrun_days, reverse=True)


async def get_monthly_trend(
    session: AsyncSession,
    licence_number: str,
    months: int = 12,
) -> list[MonthlyTrend]:
    """NC-004 — 12-month compliance trend for a single promoter."""
    today = date.today()

    stmt = select(StreetWorkRow).where(
        StreetWorkRow.promoter_licence_number == licence_number
    )
    rows = list((await session.execute(stmt)).scalars().all())

    # Group by YYYY-MM
    monthly: dict[str, list[StreetWorkRow]] = defaultdict(list)
    for row in rows:
        key = row.proposed_start_date.strftime("%Y-%m")
        monthly[key].append(row)

    results: list[MonthlyTrend] = []
    for i in range(months - 1, -1, -1):
        month_num = today.month - i
        year = today.year
        while month_num <= 0:
            month_num += 12
            year -= 1
        key = f"{year:04d}-{month_num:02d}"
        works = monthly.get(key, [])

        completed = [w for w in works if w.actual_end_date is not None]
        overruns = sum(
            1 for w in completed if w.actual_end_date.date() > w.proposed_end_date
        )
        score, *_ = _score(works, today)

        results.append(
            MonthlyTrend(
                month=key,
                compliance_score=round(score, 1),
                total_works=len(works),
                overruns=overruns,
            )
        )

    return results


def export_promoters_csv(promoters: list[PromoterComplianceRead]) -> str:
    """NC-006 — Serialise compliance data to CSV string."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Licence Number", "Promoter", "Region", "Total Works",
        "Overrun Rate %", "Late Start Rate %", "Missing Reinstatement Rate %",
        "Compliance Score", "Trend", "Last Updated",
    ])
    for p in promoters:
        writer.writerow([
            p.promoter_licence_number,
            p.promoter_name,
            p.region,
            p.total_works,
            f"{p.overrun_rate * 100:.1f}",
            f"{p.late_start_rate * 100:.1f}",
            f"{p.missing_reinstatement_rate * 100:.1f}",
            f"{p.compliance_score:.1f}",
            p.trend,
            p.last_updated,
        ])
    return buf.getvalue()
