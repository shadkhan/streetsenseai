"""UN-002 — Tests for the asset density scorer.

Strategy: pure-Python tests of the scoring helpers — no live database.
The ST_DWithin spatial query is exercised via integration tests or
Swagger UI (see browser test directions at the end of this file).
"""
from __future__ import annotations

import pytest

from services.nuar_density import (
    CORRIDOR_BUFFER_METRES,
    _ASSET_TYPE_WEIGHTS,
    _DENSITY_NORMALISER,
    classify_density_level,
    compute_density_score,
    compute_weighted_sum,
)


# ── Constants ─────────────────────────────────────────────────────────────────

def test_buffer_matches_corridor_risk() -> None:
    """UN-002 buffer must be 100 m — same as CR-002 — for scoring consistency."""
    assert CORRIDOR_BUFFER_METRES == 100.0


def test_five_utility_types_defined() -> None:
    assert set(_ASSET_TYPE_WEIGHTS.keys()) == {"gas", "electric", "water", "telecoms", "other"}


def test_gas_has_highest_weight() -> None:
    assert _ASSET_TYPE_WEIGHTS["gas"] == max(_ASSET_TYPE_WEIGHTS.values())


def test_electric_second_highest() -> None:
    sorted_weights = sorted(_ASSET_TYPE_WEIGHTS.values(), reverse=True)
    assert _ASSET_TYPE_WEIGHTS["electric"] == sorted_weights[1]


def test_telecoms_has_lowest_weight() -> None:
    assert _ASSET_TYPE_WEIGHTS["telecoms"] == min(_ASSET_TYPE_WEIGHTS.values())


def test_all_weights_positive() -> None:
    for t, w in _ASSET_TYPE_WEIGHTS.items():
        assert w > 0, f"{t} weight must be positive"


def test_normaliser_positive() -> None:
    assert _DENSITY_NORMALISER > 0


# ── compute_weighted_sum ──────────────────────────────────────────────────────

def test_weighted_sum_empty() -> None:
    assert compute_weighted_sum({}) == 0.0


def test_weighted_sum_single_gas() -> None:
    result = compute_weighted_sum({"gas": 10})
    assert result == 10 * _ASSET_TYPE_WEIGHTS["gas"]


def test_weighted_sum_mixed_types() -> None:
    assets = {"gas": 5, "electric": 3, "water": 2}
    expected = (
        5 * _ASSET_TYPE_WEIGHTS["gas"]
        + 3 * _ASSET_TYPE_WEIGHTS["electric"]
        + 2 * _ASSET_TYPE_WEIGHTS["water"]
    )
    assert abs(compute_weighted_sum(assets) - expected) < 0.001


def test_weighted_sum_unknown_type_defaults_to_one() -> None:
    """Unknown asset types default to weight 1.0 so they're not silently ignored."""
    result = compute_weighted_sum({"unknown_utility": 7})
    assert result == 7.0


def test_weighted_sum_full_synthetic_corridor() -> None:
    """Verify calibration: a single Birmingham corridor's 79 synthetic assets
    should score in the 'high' range (50–74.9) after normalisation.
    """
    # Matches _DENSITY counts from nuar_synthetic.py per corridor:
    assets = {
        "gas":      23,   # GAS_DIST_MAIN_HP(1) + MP(2) + SERVICE(20)
        "electric": 21,   # ELEC_HV(1) + LV(2) + SERVICE(18)
        "water":    20,   # WATER_TRUNK(1) + DIST(1) + SERVICE(18)
        "telecoms":  5,   # TELE_SPINE(1) + DIST(2) + COAX(1) + FIBRE(1)
        "other":    10,   # DRAIN_FOUL(5) + STORM(5)
    }
    weighted = compute_weighted_sum(assets)
    score = compute_density_score(weighted)
    # Expected: ~61 → "high"
    assert 50.0 <= score < 75.0, (
        f"Expected single-corridor score in high range, got {score}"
    )


# ── compute_density_score ─────────────────────────────────────────────────────

def test_density_score_zero_for_empty() -> None:
    assert compute_density_score(0.0) == 0.0


def test_density_score_capped_at_100() -> None:
    assert compute_density_score(99999.9) == 100.0


def test_density_score_normaliser_boundary() -> None:
    """A weighted_sum equal to the normaliser should score exactly 100."""
    assert compute_density_score(_DENSITY_NORMALISER) == 100.0


def test_density_score_half_normaliser() -> None:
    score = compute_density_score(_DENSITY_NORMALISER / 2)
    assert abs(score - 50.0) < 0.01


def test_density_score_proportional() -> None:
    s1 = compute_density_score(50.0)
    s2 = compute_density_score(100.0)
    assert abs(s2 / s1 - 2.0) < 0.01


# ── classify_density_level ────────────────────────────────────────────────────

def test_classify_low() -> None:
    assert classify_density_level(0.0) == "low"
    assert classify_density_level(24.9) == "low"


def test_classify_medium() -> None:
    assert classify_density_level(25.0) == "medium"
    assert classify_density_level(49.9) == "medium"


def test_classify_high() -> None:
    assert classify_density_level(50.0) == "high"
    assert classify_density_level(74.9) == "high"


def test_classify_critical() -> None:
    assert classify_density_level(75.0) == "critical"
    assert classify_density_level(100.0) == "critical"


def test_thresholds_match_corridor_risk() -> None:
    """UN-002 must use the same thresholds as CR-004 for UI consistency."""
    from services.corridor_risk import classify_risk_level

    for score in [0.0, 15.0, 24.9, 25.0, 40.0, 49.9, 50.0, 65.0, 74.9, 75.0, 90.0, 100.0]:
        assert classify_density_level(score) == classify_risk_level(score), (
            f"Threshold mismatch at score={score}: "
            f"density={classify_density_level(score)} "
            f"corridor={classify_risk_level(score)}"
        )


# ── AssetDensityResult schema ─────────────────────────────────────────────────

def test_asset_density_result_camelcase() -> None:
    """Schema must serialise to camelCase for the TypeScript frontend."""
    from services.nuar_density import AssetDensityResult

    result = AssetDensityResult(
        corridor_id="a38-bristol-road",
        total_assets=79,
        assets_by_type={"gas": 23},
        weighted_score=121.8,
        density_score=60.9,
        density_level="high",
        calculated_at="2026-05-14T12:00:00+00:00",
    )
    data = result.model_dump(by_alias=True)
    assert "corridorId" in data
    assert "totalAssets" in data
    assert "assetsByType" in data
    assert "weightedScore" in data
    assert "densityScore" in data
    assert "densityLevel" in data
    assert "calculatedAt" in data
    # Snake_case keys must NOT appear
    assert "corridor_id" not in data
    assert "total_assets" not in data
