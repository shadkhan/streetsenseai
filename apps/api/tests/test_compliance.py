"""NC-001 — Tests for the promoter compliance scorer.

Strategy: pure-Python unit tests of the scoring helpers, trend detection,
FPN detection, and CSV export.  DB-dependent endpoints (compute_all_promoters,
get_fpn_opportunities) are tested via Swagger UI — see end-of-file notes.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.compliance import (
    _mode,
    _score,
    _trend,
    export_promoters_csv,
)
from schemas.compliance import FPNOpportunity, PromoterComplianceRead


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_row(
    *,
    status: str = "completed",
    proposed_start: date = date(2025, 1, 1),
    proposed_end: date = date(2025, 1, 14),
    actual_start: date | None = None,
    actual_end: date | None = None,
) -> MagicMock:
    row = MagicMock()
    row.status = status
    row.proposed_start_date = proposed_start
    row.proposed_end_date = proposed_end
    row.actual_start_date = (
        datetime(actual_start.year, actual_start.month, actual_start.day, tzinfo=timezone.utc)
        if actual_start else None
    )
    row.actual_end_date = (
        datetime(actual_end.year, actual_end.month, actual_end.day, tzinfo=timezone.utc)
        if actual_end else None
    )
    return row


TODAY = date(2026, 5, 19)


# ── _mode ─────────────────────────────────────────────────────────────────────

def test_mode_most_common() -> None:
    assert _mode(["A", "B", "A", "A"]) == "A"


def test_mode_single_value() -> None:
    assert _mode(["X"]) == "X"


def test_mode_empty_returns_unknown() -> None:
    assert _mode([]) == "Unknown"


# ── _score: clean slate ───────────────────────────────────────────────────────

def test_score_empty_list_is_perfect() -> None:
    score, overrun, late, missing = _score([], TODAY)
    assert score == 100.0
    assert overrun == 0.0
    assert late == 0.0
    assert missing == 0.0


def test_score_completed_on_time_is_perfect() -> None:
    row = _make_row(
        status="completed",
        proposed_end=date(2025, 6, 1),
        actual_end=date(2025, 6, 1),
    )
    score, overrun, late, missing = _score([row], TODAY)
    assert score == 100.0
    assert overrun == 0.0


# ── _score: overrun penalty ────────────────────────────────────────────────────

def test_score_all_overrun_loses_40_points() -> None:
    row = _make_row(
        status="completed",
        proposed_end=date(2025, 6, 1),
        actual_end=date(2025, 6, 5),  # 4 days late
    )
    score, overrun, _, _ = _score([row], TODAY)
    assert overrun == 1.0
    assert score == pytest.approx(60.0)


def test_score_half_overrun_loses_20_points() -> None:
    on_time = _make_row(
        status="completed",
        proposed_end=date(2025, 6, 1),
        actual_end=date(2025, 6, 1),
    )
    late = _make_row(
        status="completed",
        proposed_end=date(2025, 6, 1),
        actual_end=date(2025, 6, 5),
    )
    score, overrun, _, _ = _score([on_time, late], TODAY)
    assert overrun == pytest.approx(0.5)
    assert score == pytest.approx(80.0)


# ── _score: late start penalty ────────────────────────────────────────────────

def test_score_all_late_start_loses_30_points() -> None:
    # proposed_end in the future so missing-reinstatement penalty doesn't fire
    row = _make_row(
        status="in_progress",
        proposed_start=date(2025, 6, 1),
        proposed_end=date(2026, 12, 31),
        actual_start=date(2025, 6, 5),
    )
    score, _, late, _ = _score([row], TODAY)
    assert late == 1.0
    assert score == pytest.approx(70.0)


def test_score_on_time_start_no_penalty() -> None:
    # proposed_end in the future so missing-reinstatement penalty doesn't fire
    row = _make_row(
        status="in_progress",
        proposed_start=date(2025, 6, 1),
        proposed_end=date(2026, 12, 31),
        actual_start=date(2025, 6, 1),
    )
    score, _, late, _ = _score([row], TODAY)
    assert late == 0.0
    assert score == pytest.approx(100.0)


# ── _score: missing reinstatement penalty ─────────────────────────────────────

def test_score_missing_reinstatement_loses_30_points() -> None:
    # in_progress + overdue proposed_end = missing reinstatement
    row = _make_row(
        status="in_progress",
        proposed_end=date(2025, 1, 1),  # well in the past
    )
    score, _, _, missing = _score([row], TODAY)
    assert missing == 1.0
    assert score == pytest.approx(70.0)


def test_score_in_progress_not_overdue_no_penalty() -> None:
    row = _make_row(
        status="in_progress",
        proposed_end=date(2026, 12, 31),  # future
    )
    score, _, _, missing = _score([row], TODAY)
    assert missing == 0.0


# ── _score: floor clamping ────────────────────────────────────────────────────

def test_score_cannot_go_below_zero() -> None:
    # Worst possible: all three penalties at 100%
    overrun_row = _make_row(
        status="completed",
        proposed_end=date(2025, 6, 1),
        actual_end=date(2025, 6, 5),
    )
    late_start_row = _make_row(
        status="in_progress",
        proposed_start=date(2025, 6, 1),
        actual_start=date(2025, 6, 5),
        proposed_end=date(2025, 1, 1),  # also overdue (missing reinstatement)
    )
    score, *_ = _score([overrun_row, late_start_row], TODAY)
    assert score >= 0.0


# ── _trend ────────────────────────────────────────────────────────────────────

def test_trend_improving_when_recent_much_better() -> None:
    from datetime import timedelta
    today = date(2026, 5, 19)
    six_ago = today - timedelta(days=182)
    twelve_ago = today - timedelta(days=365)

    # Good recent works (no overruns)
    recent_good = _make_row(
        proposed_start=today - timedelta(days=30),
        proposed_end=date(2026, 4, 1),
        actual_end=date(2026, 4, 1),
    )
    # Bad old works (all overrun)
    old_bad = _make_row(
        proposed_start=twelve_ago + timedelta(days=10),
        proposed_end=date(2025, 12, 1),
        actual_end=date(2025, 12, 20),
    )
    trend = _trend([recent_good, old_bad], today)
    assert trend == "improving"


def test_trend_stable_when_similar_scores() -> None:
    from datetime import timedelta
    today = date(2026, 5, 19)

    rows = [
        _make_row(
            proposed_start=today - timedelta(days=i * 20),
            proposed_end=date(2026, 1, 1),
            actual_end=date(2026, 1, 1),
        )
        for i in range(10)
    ]
    trend = _trend(rows, today)
    # All on-time in both windows → stable
    assert trend == "stable"


# ── export_promoters_csv ──────────────────────────────────────────────────────

def _make_promoter(**kwargs) -> PromoterComplianceRead:
    defaults = dict(
        promoter_licence_number="LIC001",
        promoter_name="Test Promoter Ltd",
        total_works=42,
        overrun_rate=0.15,
        late_start_rate=0.10,
        missing_reinstatement_rate=0.05,
        compliance_score=73.5,
        trend="stable",
        region="Birmingham City Council",
        last_updated="2026-05-19T10:00:00+00:00",
    )
    defaults.update(kwargs)
    return PromoterComplianceRead(**defaults)


def test_csv_has_header_row() -> None:
    csv = export_promoters_csv([])
    first_line = csv.splitlines()[0]
    assert "Licence Number" in first_line
    assert "Compliance Score" in first_line


def test_csv_has_correct_row_count() -> None:
    promoters = [_make_promoter(promoter_licence_number=f"LIC{i:03d}") for i in range(5)]
    csv = export_promoters_csv(promoters)
    lines = [l for l in csv.splitlines() if l.strip()]
    assert len(lines) == 6  # 1 header + 5 data rows


def test_csv_contains_promoter_data() -> None:
    p = _make_promoter(
        promoter_licence_number="TEST123",
        promoter_name="Acme Excavation",
        compliance_score=88.5,
    )
    csv = export_promoters_csv([p])
    assert "TEST123" in csv
    assert "Acme Excavation" in csv
    assert "88.5" in csv


def test_csv_rates_as_percentages() -> None:
    p = _make_promoter(overrun_rate=0.25)
    csv = export_promoters_csv([p])
    # Should be "25.0" not "0.25"
    assert "25.0" in csv
    assert "0.25" not in csv


def test_csv_empty_list_has_only_header() -> None:
    csv = export_promoters_csv([])
    lines = [l for l in csv.splitlines() if l.strip()]
    assert len(lines) == 1


# ── FPNOpportunity schema ─────────────────────────────────────────────────────

def test_fpn_camel_case_alias() -> None:
    fpn = FPNOpportunity(
        permit_reference="ABC/2025/001",
        promoter="Test Ltd",
        promoter_licence_number="LIC001",
        street_name="High Street",
        authority="Birmingham",
        proposed_end_date="2025-06-01",
        actual_end_date="2025-06-08",
        overrun_days=7,
    )
    dumped = fpn.model_dump(by_alias=True)
    assert "permitReference" in dumped
    assert "overrunDays" in dumped
    assert dumped["overrunDays"] == 7


# ── Swagger UI test notes ─────────────────────────────────────────────────────
#
# The following endpoints require a live DB with synthetic data seeded:
#
#   1. Seed data:  POST /works/admin/seed
#
#   2. GET /compliance/summary
#      Expect: { totalPromoters: N, avgComplianceScore: 0–100,
#                worstOffender: {...}, totalFpnOpportunities: N }
#
#   3. GET /compliance/promoters
#      Expect: array sorted by complianceScore ascending (worst first).
#      Each item has overrunRate, lateStartRate, missingReinstatementRate as 0–1.
#
#   4. GET /compliance/promoters/{licence_number}/monthly-trend
#      Copy a licenceNumber from step 3. Expect 12 objects with month="YYYY-MM".
#
#   5. GET /compliance/fpn-opportunities
#      Expect: completed/closed works where actual_end_date > proposed_end_date,
#      sorted by overrunDays desc.
#
#   6. GET /compliance/export/promoters.csv
#      Should trigger a file download. Open in Excel — verify columns and rates
#      show as percentages (e.g. "15.0" not "0.15").
#
#   7. GET /compliance/briefing/generate
#      Should stream plain text. Watch the response build word by word.
