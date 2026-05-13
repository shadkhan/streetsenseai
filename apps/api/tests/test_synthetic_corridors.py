"""Tests for CR-001: synthetic corridor generator."""
from __future__ import annotations

from services.synthetic.corridor_generator import SyntheticCorridorGenerator

_UK_BBOX = (-8.5, 49.5, 2.0, 60.5)
_VALID_CLASSIFICATIONS = {"A", "B", "C", "unclassified"}


def _make_gen(seed: int = 42) -> SyntheticCorridorGenerator:
    return SyntheticCorridorGenerator(seed=seed)


def test_corridor_count() -> None:
    """generate_all() must return exactly 40 corridors (one per corridors.json entry)."""
    gen = _make_gen()
    corridors = gen.generate_all()
    assert len(corridors) == 40, f"Expected 40 corridors, got {len(corridors)}"


def test_corridor_geometry_type() -> None:
    """Every corridor geometry must be a LineString."""
    gen = _make_gen()
    for c in gen.generate_all():
        assert c.geometry.type == "LineString", f"Corridor {c.id} has non-LineString geometry"


def test_corridor_min_points() -> None:
    """Every corridor LineString must have at least 3 coordinate pairs."""
    gen = _make_gen()
    for c in gen.generate_all():
        assert len(c.geometry.coordinates) >= 3, (
            f"Corridor {c.id} has only {len(c.geometry.coordinates)} points"
        )


def test_corridor_coordinates_in_uk() -> None:
    """All corridor coordinates must fall within the UK bounding box."""
    min_lng, min_lat, max_lng, max_lat = _UK_BBOX
    gen = _make_gen()
    for c in gen.generate_all():
        for lng, lat in c.geometry.coordinates:
            assert min_lng <= lng <= max_lng, f"{c.id}: lng {lng} out of UK bounds"
            assert min_lat <= lat <= max_lat, f"{c.id}: lat {lat} out of UK bounds"


def test_corridor_ids_unique() -> None:
    """No two corridors may share the same ID."""
    gen = _make_gen()
    ids = [c.id for c in gen.generate_all()]
    assert len(ids) == len(set(ids)), "Duplicate corridor IDs detected"


def test_corridor_classification_valid() -> None:
    """Every corridor must have a valid road classification."""
    gen = _make_gen()
    for c in gen.generate_all():
        assert c.road_classification in _VALID_CLASSIFICATIONS, (
            f"Corridor {c.id} has invalid classification '{c.road_classification}'"
        )


def test_corridor_source_is_synthetic() -> None:
    """Synthetic generator must set source='synthetic' on every corridor."""
    gen = _make_gen()
    for c in gen.generate_all():
        assert c.source == "synthetic", f"Corridor {c.id} has unexpected source '{c.source}'"


def test_corridor_determinism() -> None:
    """Same seed must produce identical coordinates on two separate instances."""
    gen_a = _make_gen(seed=42)
    gen_b = _make_gen(seed=42)
    corridors_a = gen_a.generate_all()
    corridors_b = gen_b.generate_all()
    for a, b in zip(corridors_a, corridors_b):
        assert a.model_dump() == b.model_dump(), f"Non-deterministic output for {a.id}"


def test_corridor_generate_by_id() -> None:
    """generate_by_id must return the correct corridor and None for unknown IDs."""
    gen = _make_gen()
    c = gen.generate_by_id("a38-birmingham-city-centre")
    assert c is not None
    assert c.id == "a38-birmingham-city-centre"
    assert c.road_classification == "A"
    assert gen.generate_by_id("does-not-exist") is None


def test_corridor_name_not_empty() -> None:
    """Every corridor must have a non-empty name."""
    gen = _make_gen()
    for c in gen.generate_all():
        assert c.name.strip(), f"Corridor {c.id} has an empty name"
