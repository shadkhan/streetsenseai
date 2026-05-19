"""UN-006 — Tests for the composite risk scorer.

Strategy: unit-test the formula and classification logic directly.
DB-dependent integration (actual corridor + NUAR data) is tested via
Swagger UI — see end-of-file notes.
"""
from __future__ import annotations

import pytest

from services.composite_risk import (
    SURFACE_WEIGHT,
    UNDERGROUND_WEIGHT,
    CompositeRiskResult,
)
from services.corridor_risk import classify_risk_level


# ── Weight constants ──────────────────────────────────────────────────────────

def test_weights_sum_to_one() -> None:
    assert SURFACE_WEIGHT + UNDERGROUND_WEIGHT == pytest.approx(1.0)


def test_surface_weight_is_60_pct() -> None:
    assert SURFACE_WEIGHT == pytest.approx(0.60)


def test_underground_weight_is_40_pct() -> None:
    assert UNDERGROUND_WEIGHT == pytest.approx(0.40)


# ── Formula verification ──────────────────────────────────────────────────────

def _composite(surface: float, underground: float) -> float:
    return round(surface * SURFACE_WEIGHT + underground * UNDERGROUND_WEIGHT, 2)


def test_formula_all_surface_no_underground() -> None:
    # 100 surface, 0 underground → 60% of 100 = 60
    assert _composite(100.0, 0.0) == pytest.approx(60.0)


def test_formula_equal_scores() -> None:
    # 80 surface, 80 underground → 80
    assert _composite(80.0, 80.0) == pytest.approx(80.0)


def test_formula_zero_both() -> None:
    assert _composite(0.0, 0.0) == pytest.approx(0.0)


def test_formula_max_both() -> None:
    assert _composite(100.0, 100.0) == pytest.approx(100.0)


def test_formula_high_surface_low_underground() -> None:
    # surface=80 underground=20 → 80*0.6 + 20*0.4 = 48 + 8 = 56
    assert _composite(80.0, 20.0) == pytest.approx(56.0)


def test_formula_low_surface_high_underground() -> None:
    # surface=20 underground=80 → 20*0.6 + 80*0.4 = 12 + 32 = 44
    assert _composite(20.0, 80.0) == pytest.approx(44.0)


# ── Composite level classification ────────────────────────────────────────────
# Uses the same thresholds as CR-004 — verified here to confirm UN-006 re-uses them

def test_composite_level_low() -> None:
    assert classify_risk_level(_composite(30.0, 0.0)) == "low"   # 18


def test_composite_level_medium() -> None:
    assert classify_risk_level(_composite(60.0, 0.0)) == "medium"  # 36


def test_composite_level_high() -> None:
    assert classify_risk_level(_composite(90.0, 20.0)) == "high"  # 62


def test_composite_level_critical() -> None:
    assert classify_risk_level(_composite(100.0, 100.0)) == "critical"  # 100


def test_composite_level_boundary_medium_to_high() -> None:
    # surface=80 underground=5 → 48 + 2 = 50.0 → high (≥50)
    score = _composite(80.0, 5.0)
    assert score == pytest.approx(50.0)
    assert classify_risk_level(score) == "high"


# ── Schema camelCase aliases ──────────────────────────────────────────────────

def test_schema_camel_aliases() -> None:
    result = CompositeRiskResult(
        corridor_id="a38-bham",
        surface_score=72.0,
        surface_level="high",
        underground_score=45.0,
        underground_level="medium",
        composite_score=_composite(72.0, 45.0),
        composite_level="high",
        surface_weight=SURFACE_WEIGHT,
        underground_weight=UNDERGROUND_WEIGHT,
        underground_assets_in_range=23,
        calculated_at="2026-05-19T10:00:00+00:00",
    )
    dumped = result.model_dump(by_alias=True)
    assert "corridorId" in dumped
    assert "surfaceScore" in dumped
    assert "undergroundScore" in dumped
    assert "compositeScore" in dumped
    assert "compositeLevel" in dumped
    assert "undergroundAssetsInRange" in dumped
    assert dumped["surfaceWeight"] == pytest.approx(0.60)
    assert dumped["undergroundWeight"] == pytest.approx(0.40)


def test_schema_composite_score_matches_formula() -> None:
    surface, underground = 65.0, 50.0
    expected = _composite(surface, underground)
    result = CompositeRiskResult(
        corridor_id="test",
        surface_score=surface,
        surface_level="high",
        underground_score=underground,
        underground_level="medium",
        composite_score=expected,
        composite_level=classify_risk_level(expected),
        surface_weight=SURFACE_WEIGHT,
        underground_weight=UNDERGROUND_WEIGHT,
        underground_assets_in_range=12,
        calculated_at="2026-05-19T10:00:00+00:00",
    )
    assert result.composite_score == pytest.approx(expected)


# ── Swagger UI test notes ─────────────────────────────────────────────────────
#
# 1. Seed works:  POST /works/admin/seed
# 2. Seed NUAR:   POST /nuar/admin/seed
# 3. Seed scores: POST /corridors/admin/score  (or wait for Celery hourly task)
#
# 4. GET /corridors  → copy any corridor ID
#
# 5. GET /corridors/{id}/composite-risk
#    Expect:
#      compositeScore: 0–100
#      compositeLevel: low | medium | high | critical
#      surfaceScore: 0–100 (same as corridor.riskScore)
#      surfaceLevel: matches corridor.riskLevel
#      undergroundScore: 0–100 (from UN-002 density)
#      undergroundAssetsInRange: N > 0 if NUAR seeded
#      surfaceWeight: 0.6
#      undergroundWeight: 0.4
#
# 6. Verify: compositeScore ≈ surfaceScore × 0.6 + undergroundScore × 0.4
#
# 7. Open a corridor on the map → CorridorSheet should show
#    "Composite Risk" section with two coloured progress bars.
