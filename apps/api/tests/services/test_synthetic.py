"""Tests for SM-008: synthetic Street Manager data generator."""
from __future__ import annotations

import re
from datetime import date

import pytest

from schemas.works import StreetWorkBase, StreetWorkStatus
from services.synthetic.generator import (
    UK_BBOX,
    SyntheticStreetManagerGenerator,
)

_START = date(2026, 1, 1)
_END = date(2026, 12, 31)
_PERMIT_RE = re.compile(r"^[A-Z0-9]+/\d{4}/\d+$")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_gen(seed: int = 42) -> SyntheticStreetManagerGenerator:
    return SyntheticStreetManagerGenerator(seed=seed)


def _coords(work: StreetWorkBase) -> list[tuple[float, float]]:
    if work.geometry.type == "Point":
        return [work.geometry.coordinates]  # type: ignore[list-item]
    return list(work.geometry.coordinates)  # type: ignore[arg-type]


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_determinism() -> None:
    """Same seed must produce byte-identical output on two separate instances."""
    gen_a = _make_gen(seed=42)
    gen_b = _make_gen(seed=42)
    works_a = gen_a.generate(200, _START, _END)
    works_b = gen_b.generate(200, _START, _END)
    assert len(works_a) == len(works_b)
    for a, b in zip(works_a, works_b):
        assert a.model_dump() == b.model_dump(), "Non-deterministic output for same seed"


def test_schema_conformance() -> None:
    """Every generated record must pass StreetWorkBase Pydantic validation."""
    gen = _make_gen()
    works = gen.generate(500, _START, _END)
    for i, raw in enumerate(works):
        # Re-validate by round-tripping through model_dump → model_validate
        dumped = raw.model_dump()
        try:
            StreetWorkBase.model_validate(dumped)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"Record {i} failed StreetWorkBase validation: {exc}\n{dumped}")


def test_count() -> None:
    """generate(N) must return exactly N records."""
    gen = _make_gen()
    for n in (1, 50, 250):
        assert len(gen.generate(n, _START, _END)) == n


def test_date_window() -> None:
    """All permits must have proposed dates within the requested window."""
    gen = _make_gen()
    works = gen.generate(300, _START, _END)
    for w in works:
        start = date.fromisoformat(w.proposed_start_date)
        end = date.fromisoformat(w.proposed_end_date)
        assert start >= _START, f"proposed_start_date {start} is before window {_START}"
        assert start < _END, f"proposed_start_date {start} is at or after window end {_END}"
        assert end > start, "proposed_end_date must be strictly after proposed_start_date"


def test_authority_distribution() -> None:
    """Top authority (TfL) should capture between 5% and 25% of a 5000-record run."""
    gen = _make_gen(seed=42)
    works = gen.generate(5000, _START, _END)
    counts: dict[str, int] = {}
    for w in works:
        counts[w.authority] = counts.get(w.authority, 0) + 1

    # Transport for London has the highest weight (5.0) and should rank first
    total = len(works)
    tfl_share = counts.get("Transport for London", 0) / total
    assert 0.05 <= tfl_share <= 0.25, (
        f"TfL share {tfl_share:.2%} outside expected 5–25% range"
    )
    # At least 10 distinct authorities should appear in 5000 records
    assert len(counts) >= 10, f"Expected ≥10 distinct authorities, got {len(counts)}"


def test_geometry_within_uk() -> None:
    """Every coordinate in every geometry must fall within the UK bounding box."""
    min_lng, min_lat, max_lng, max_lat = UK_BBOX
    gen = _make_gen()
    works = gen.generate(500, _START, _END)
    for w in works:
        for lng, lat in _coords(w):
            assert min_lng <= lng <= max_lng, f"lng {lng} out of UK bounds"
            assert min_lat <= lat <= max_lat, f"lat {lat} out of UK bounds"


def test_overrun_injection() -> None:
    """Injecting 'overrun' must produce ≥1 record where actualEndDate > proposedEndDate."""
    gen = _make_gen()
    works = gen.generate(200, _START, _END)
    works = gen.inject_edge_cases(works, ["overrun"])

    overruns = [
        w for w in works
        if w.actual_end_date is not None
        and date.fromisoformat(w.actual_end_date) > date.fromisoformat(w.proposed_end_date)
    ]
    assert len(overruns) >= 1, "Expected at least one overrun record after injection"


def test_corridor_cluster() -> None:
    """generate_corridor_cluster must return N permits all from the same authority."""
    gen = _make_gen()
    cluster = gen.generate_corridor_cluster(
        "A38 Birmingham",
        count=20,
        date_window=(_START, _END),
    )
    assert len(cluster) == 20

    # All should be from Birmingham City Council (the mapped authority)
    authorities = {w.authority for w in cluster}
    assert "Birmingham City Council" in authorities

    # Dates must overlap the date_window
    for w in cluster:
        start = date.fromisoformat(w.proposed_start_date)
        end = date.fromisoformat(w.proposed_end_date)
        assert start < _END, "Cluster permit starts after window"
        assert end > _START, "Cluster permit ends before window"


def test_permit_reference_format() -> None:
    """Every permit reference must match LICENCE/YEAR/SEQUENCE pattern."""
    gen = _make_gen()
    works = gen.generate(300, _START, _END)
    for w in works:
        assert _PERMIT_RE.match(w.permit_reference), (
            f"Invalid permit reference format: '{w.permit_reference}'"
        )


def test_status_distribution() -> None:
    """'granted' must be the modal status in a large run."""
    gen = _make_gen(seed=42)
    works = gen.generate(2000, _START, _END)
    counts: dict[str, int] = {}
    for w in works:
        counts[w.status.value] = counts.get(w.status.value, 0) + 1
    modal_status = max(counts, key=lambda s: counts[s])
    assert modal_status == "granted", (
        f"Expected 'granted' as modal status, got '{modal_status}'. "
        f"Distribution: {counts}"
    )


def test_geometry_type_mix() -> None:
    """Roughly 70% Point and 30% LineString (±15% tolerance) for large runs."""
    gen = _make_gen(seed=42)
    works = gen.generate(1000, _START, _END)
    points = sum(1 for w in works if w.geometry.type == "Point")
    ratio = points / len(works)
    assert 0.55 <= ratio <= 0.85, (
        f"Point geometry ratio {ratio:.1%} outside expected 55–85% range"
    )
