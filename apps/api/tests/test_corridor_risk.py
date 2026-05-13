"""Tests for CR-002/003/004: corridor risk scoring engine.

Covers pure functions (classify_risk_level, compute_risk_score) exhaustively.
get_works_near_corridor and score_corridor require PostGIS and are tested via
integration when a live DB is available — not here.
"""
from __future__ import annotations



from schemas.domain import PointGeometry, StreetWork
from services.corridor_risk import (
    classify_risk_level,
    compute_risk_score,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _work(
    permit: str = "WG7/2026/00001234",
    traffic_management: str = "two_way_signals",
    work_type: str = "standard",
    status: str = "in_progress",
) -> StreetWork:
    return StreetWork(
        permit_reference=permit,
        usrn="41507223",
        street_name="Corporation Street",
        authority="Birmingham City Council",
        promoter="Cadent Gas",
        promoter_licence_number="WG7",
        work_type=work_type,
        traffic_management_type=traffic_management,
        restriction_type="Lane closure",
        proposed_start_date="2026-05-01",
        proposed_end_date="2026-05-14",
        status=status,  # type: ignore[arg-type]
        geometry=PointGeometry(type="Point", coordinates=(-1.902, 52.486)),
    )


# ── CR-004: classify_risk_level ────────────────────────────────────────────────

def test_classify_low_boundary() -> None:
    assert classify_risk_level(0.0) == "low"
    assert classify_risk_level(24.9) == "low"


def test_classify_medium_boundary() -> None:
    assert classify_risk_level(25.0) == "medium"
    assert classify_risk_level(49.9) == "medium"


def test_classify_high_boundary() -> None:
    assert classify_risk_level(50.0) == "high"
    assert classify_risk_level(74.9) == "high"


def test_classify_critical_boundary() -> None:
    assert classify_risk_level(75.0) == "critical"
    assert classify_risk_level(100.0) == "critical"


# ── CR-003: compute_risk_score — zero works ────────────────────────────────────

def test_no_works_returns_zero_score() -> None:
    score, factors = compute_risk_score([], "A")
    assert score == 0.0
    assert factors == []


def test_no_works_classifies_as_low() -> None:
    score, _ = compute_risk_score([], "unclassified")
    assert classify_risk_level(score) == "low"


# ── CR-003: compute_risk_score — with works ────────────────────────────────────

def test_works_produce_nonzero_score() -> None:
    score, _ = compute_risk_score([_work()], "A")
    assert score > 0.0


def test_score_bounded_0_to_100() -> None:
    """Score must always be in [0, 100] regardless of inputs."""
    many = [_work(f"REF/{i}", "road_closure", "major") for i in range(20)]
    score, _ = compute_risk_score(many, "A")
    assert 0.0 <= score <= 100.0


def test_factor_contributions_sum_to_score() -> None:
    """Sum of all factor contributions must equal the returned score."""
    works = [_work("A", "lane_closure", "standard"), _work("B", "two_way_signals", "minor")]
    score, factors = compute_risk_score(works, "B")
    assert abs(sum(f.contribution for f in factors) - score) < 0.01


def test_four_factors_returned() -> None:
    """compute_risk_score always returns exactly four factors when works exist."""
    _, factors = compute_risk_score([_work()], "A")
    assert len(factors) == 4
    names = {f.factor for f in factors}
    assert names == {"concurrent_works", "traffic_management", "work_type", "road_classification"}


def test_factor_weights_sum_to_one() -> None:
    """Declared weights must sum to 1.0."""
    from services.corridor_risk import _W_COUNT, _W_ROAD_CLASS, _W_TRAFFIC, _W_WORK_TYPE
    total = _W_COUNT + _W_TRAFFIC + _W_WORK_TYPE + _W_ROAD_CLASS
    assert abs(total - 1.0) < 1e-9


# ── CR-003: road classification weight ────────────────────────────────────────

def test_a_road_scores_higher_than_unclassified() -> None:
    """Same works on an A road must score higher than on an unclassified road."""
    works = [_work()]
    score_a, _ = compute_risk_score(works, "A")
    score_u, _ = compute_risk_score(works, "unclassified")
    assert score_a > score_u


def test_road_classification_ordering() -> None:
    """Risk from road classification: A > B > C > unclassified."""
    works = [_work()]
    scores = {cls: compute_risk_score(works, cls)[0] for cls in ("A", "B", "C", "unclassified")}
    assert scores["A"] > scores["B"] > scores["C"] > scores["unclassified"]


# ── CR-003: traffic management weight ─────────────────────────────────────────

def test_road_closure_scores_higher_than_signals() -> None:
    score_closure, _ = compute_risk_score([_work(traffic_management="road_closure")], "B")
    score_signals, _ = compute_risk_score([_work(traffic_management="two_way_signals")], "B")
    assert score_closure > score_signals


def test_unknown_traffic_management_defaults_gracefully() -> None:
    """Unknown traffic management type should not raise — defaults to 0."""
    score, _ = compute_risk_score([_work(traffic_management="some_unknown_type")], "A")
    assert 0.0 <= score <= 100.0


# ── CR-003: work type weight ───────────────────────────────────────────────────

def test_major_work_scores_higher_than_minor() -> None:
    score_major, _ = compute_risk_score([_work(work_type="major")], "B")
    score_minor, _ = compute_risk_score([_work(work_type="minor")], "B")
    assert score_major > score_minor


# ── CR-003: concurrent works count ────────────────────────────────────────────

def test_more_works_higher_score() -> None:
    one = [_work("A")]
    three = [_work("A"), _work("B"), _work("C")]
    score_one, _ = compute_risk_score(one, "B")
    score_three, _ = compute_risk_score(three, "B")
    assert score_three > score_one


def test_count_factor_caps_at_four_works() -> None:
    """Score with 4 works must equal score with 8 works — count caps at 4."""
    four = [_work(str(i)) for i in range(4)]
    eight = [_work(str(i)) for i in range(8)]
    score_four, _ = compute_risk_score(four, "B")
    score_eight, _ = compute_risk_score(eight, "B")
    assert score_four == score_eight


# ── RiskFactor structure ───────────────────────────────────────────────────────

def test_risk_factor_fields_present() -> None:
    _, factors = compute_risk_score([_work()], "A")
    for f in factors:
        assert isinstance(f.factor, str) and f.factor
        assert 0.0 <= f.weight <= 1.0
        assert f.contribution >= 0.0
        assert isinstance(f.description, str) and f.description
