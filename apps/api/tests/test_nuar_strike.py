"""UN-003 — Tests for the strike risk classifier.

Strategy: pure-Python unit tests of the scoring helpers and schema serialisation.
The ST_DWithin spatial query and DB persistence are tested via Swagger UI
(see browser test directions at end of session).
"""
from __future__ import annotations

import pytest

from services.nuar_strike import (
    CACHE_SECONDS,
    STRIKE_BUFFER_METRES,
    _COUNT_BONUS_CAP,
    _COUNT_BONUS_PER_ASSET,
    _DIVERSITY_FACTOR,
    _TYPE_RISK_BASE,
    classify_strike_level,
    compute_strike_score,
    identify_highest_risk_asset,
)


# ── Constants ─────────────────────────────────────────────────────────────────

def test_strike_buffer_25m() -> None:
    assert STRIKE_BUFFER_METRES == 25.0


def test_cache_seconds_5min() -> None:
    assert CACHE_SECONDS == 300


def test_five_risk_types_defined() -> None:
    assert set(_TYPE_RISK_BASE.keys()) == {"gas", "electric", "water", "telecoms", "other"}


def test_gas_highest_risk() -> None:
    assert _TYPE_RISK_BASE["gas"] == max(_TYPE_RISK_BASE.values())


def test_electric_second() -> None:
    sorted_vals = sorted(_TYPE_RISK_BASE.values(), reverse=True)
    assert _TYPE_RISK_BASE["electric"] == sorted_vals[1]


def test_all_base_scores_positive() -> None:
    for t, v in _TYPE_RISK_BASE.items():
        assert v > 0, f"{t} base score must be positive"


def test_count_bonus_cap_positive() -> None:
    assert _COUNT_BONUS_CAP > 0
    assert _COUNT_BONUS_PER_ASSET > 0


# ── compute_strike_score ──────────────────────────────────────────────────────

def test_score_empty_no_assets() -> None:
    assert compute_strike_score({}) == 0.0


def test_score_single_gas_is_high() -> None:
    """One gas asset → score ≥ 50 (high territory)."""
    score = compute_strike_score({"gas": 1})
    assert score >= 50.0
    assert classify_strike_level(score) == "high"


def test_score_single_telecoms_is_low() -> None:
    score = compute_strike_score({"telecoms": 1})
    assert classify_strike_level(score) == "low"


def test_score_single_water_is_medium() -> None:
    score = compute_strike_score({"water": 1})
    assert classify_strike_level(score) in {"low", "medium"}
    # Water score (25) sits exactly at the medium threshold
    assert score >= 25.0


def test_score_gas_and_electric_is_high_or_critical() -> None:
    score = compute_strike_score({"gas": 1, "electric": 1})
    assert classify_strike_level(score) in {"high", "critical"}


def test_score_many_gas_assets_critical() -> None:
    score = compute_strike_score({"gas": 10})
    assert classify_strike_level(score) == "critical"


def test_count_bonus_caps() -> None:
    """Adding 1000 assets should not exceed 100."""
    score = compute_strike_score({"gas": 1000})
    assert score <= 100.0


def test_score_full_synthetic_load_critical() -> None:
    """All utility types present (full Birmingham corridor) → critical."""
    assets = {"gas": 23, "electric": 21, "water": 20, "telecoms": 5, "other": 10}
    score = compute_strike_score(assets)
    assert score <= 100.0
    assert classify_strike_level(score) == "critical"


def test_score_proportional_to_count() -> None:
    """More assets of the same type → equal or higher score."""
    s1 = compute_strike_score({"water": 1})
    s2 = compute_strike_score({"water": 5})
    assert s2 >= s1


def test_score_diversity_increases_score() -> None:
    """Adding a second utility type increases score."""
    base = compute_strike_score({"gas": 1})
    with_water = compute_strike_score({"gas": 1, "water": 1})
    assert with_water > base


# ── classify_strike_level ─────────────────────────────────────────────────────

def test_classify_boundaries() -> None:
    assert classify_strike_level(0.0) == "low"
    assert classify_strike_level(24.9) == "low"
    assert classify_strike_level(25.0) == "medium"
    assert classify_strike_level(49.9) == "medium"
    assert classify_strike_level(50.0) == "high"
    assert classify_strike_level(74.9) == "high"
    assert classify_strike_level(75.0) == "critical"
    assert classify_strike_level(100.0) == "critical"


def test_classify_matches_corridor_risk_thresholds() -> None:
    """UN-003 must use the same classification thresholds as CR-004."""
    from services.corridor_risk import classify_risk_level

    for score in [0.0, 10.0, 24.9, 25.0, 37.5, 49.9, 50.0, 62.5, 74.9, 75.0, 90.0, 100.0]:
        assert classify_strike_level(score) == classify_risk_level(score), (
            f"Mismatch at score={score}"
        )


# ── identify_highest_risk_asset ────────────────────────────────────────────────

def test_highest_risk_none_for_empty() -> None:
    result = identify_highest_risk_asset({}, {})
    assert result is None


def test_highest_risk_picks_gas_over_telecoms() -> None:
    result = identify_highest_risk_asset(
        {"gas": 2, "telecoms": 10},
        {"gas": "Cadent Gas Ltd", "telecoms": "BT Openreach"},
    )
    assert result is not None
    assert result.type == "gas"
    assert result.operator == "Cadent Gas Ltd"


def test_highest_risk_level_reflects_solo_score() -> None:
    """The risk level on the highest-risk asset should reflect its solo score."""
    result = identify_highest_risk_asset({"gas": 1}, {"gas": "Cadent Gas Ltd"})
    assert result is not None
    solo_score = compute_strike_score({"gas": 1})
    expected_level = classify_strike_level(solo_score)
    assert result.risk == expected_level


def test_highest_risk_unknown_operator_fallback() -> None:
    result = identify_highest_risk_asset({"electric": 3}, {})
    assert result is not None
    assert result.operator == "Unknown"


# ── Schema serialisation ──────────────────────────────────────────────────────

def test_strike_risk_create_camelcase() -> None:
    from schemas.nuar import HighestRiskAsset, StrikeRiskCreate

    data = StrikeRiskCreate(
        permit_reference="WG7/2026/00001234",
        overall_risk="high",
        asset_count=5,
        assets_by_type={"gas": 3, "water": 2},
        highest_risk_asset=HighestRiskAsset(
            type="gas", operator="Cadent Gas Ltd", risk="high"
        ),
    )
    dumped = data.model_dump(by_alias=True)
    assert "permitReference" in dumped
    assert "overallRisk" in dumped
    assert "assetCount" in dumped
    assert "assetsByType" in dumped
    assert "highestRiskAsset" in dumped
    # Snake_case must not appear
    assert "permit_reference" not in dumped
    assert "overall_risk" not in dumped


def test_strike_risk_create_accepts_snakecase_input() -> None:
    """populate_by_name=True allows Python code to use snake_case."""
    from schemas.nuar import StrikeRiskCreate

    obj = StrikeRiskCreate(
        permit_reference="WG7/2026/00001234",
        overall_risk="critical",
        asset_count=10,
        assets_by_type={"gas": 10},
    )
    assert obj.permit_reference == "WG7/2026/00001234"
    assert obj.overall_risk == "critical"


def test_highest_risk_asset_camelcase() -> None:
    from schemas.nuar import HighestRiskAsset

    asset = HighestRiskAsset(type="gas", operator="Cadent", risk="high")
    # HighestRiskAsset fields have no underscores, so camelCase == snake_case here
    dumped = asset.model_dump(by_alias=True)
    assert dumped["type"] == "gas"
    assert dumped["operator"] == "Cadent"
    assert dumped["risk"] == "high"


def test_strike_risk_asset_count_non_negative() -> None:
    from schemas.nuar import StrikeRiskCreate

    with pytest.raises(Exception):
        StrikeRiskCreate(
            permit_reference="X",
            overall_risk="low",
            asset_count=-1,
            assets_by_type={},
        )
