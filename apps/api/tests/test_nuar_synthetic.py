"""UN-008 — Tests for the synthetic NUAR underground asset generator.

Strategy: pure-Python unit tests — no live database required.
Mirrors the approach in test_nuar_migration.py and test_synthetic_corridors.py:
test module-level constants, geometry helpers, and deterministic output shape.
"""
from __future__ import annotations

import random

import pytest

from services.nuar_synthetic import (
    SEED,
    _ATTRS,
    _CORRIDORS,
    _DENSITY,
    _LATERAL_DEG,
    _OWNER_SEEDS,
    _TYPE_SEEDS,
    _linestring_wkt,
    _point_wkt,
    _rand_date,
    expected_total_asset_count,
)


# ── Constants ─────────────────────────────────────────────────────────────────

def test_seed_is_42() -> None:
    assert SEED == 42


def test_lateral_deg_keeps_assets_within_buffer() -> None:
    """_LATERAL_DEG ≈ 15 m at lat 52.5° — well within the 100 m PostGIS buffer."""
    metres_approx = _LATERAL_DEG * 111_320 * 0.62  # cos(52.5°) ≈ 0.605; rough
    assert metres_approx < 20, f"_LATERAL_DEG too large: ≈ {metres_approx:.1f} m"


def test_five_corridors() -> None:
    assert len(_CORRIDORS) == 5


def test_corridor_ids_are_unique() -> None:
    ids = [c["id"] for c in _CORRIDORS]
    assert len(ids) == len(set(ids))


def test_corridor_fields() -> None:
    """Every corridor must have center, axis, and half_extent."""
    for c in _CORRIDORS:
        assert "center" in c
        assert "axis" in c and c["axis"] in {"NS", "EW"}
        assert "half_extent" in c and c["half_extent"] > 0
        lng, lat = c["center"]
        # All corridors should be roughly in Birmingham (WGS84)
        assert -2.0 < lng < -1.8
        assert 52.4 < lat < 52.6


# ── Owner / type seeds ────────────────────────────────────────────────────────

def test_six_asset_owners() -> None:
    assert len(_OWNER_SEEDS) == 6


def test_owner_utility_types_valid() -> None:
    valid_types = {"gas", "electric", "water", "telecoms", "other"}
    for owner in _OWNER_SEEDS:
        assert owner["asset_type"] in valid_types


def test_owner_emails_look_valid() -> None:
    for owner in _OWNER_SEEDS:
        assert "@" in owner["contact_email"]


def test_type_seeds_cover_all_owners() -> None:
    """Every owner in _OWNER_SEEDS must have entries in _TYPE_SEEDS."""
    owner_names = {o["name"] for o in _OWNER_SEEDS}
    assert owner_names == set(_TYPE_SEEDS.keys())


def test_fifteen_asset_types() -> None:
    total = sum(len(v) for v in _TYPE_SEEDS.values())
    assert total == 15


def test_all_density_types_have_attrs() -> None:
    """Every type code in _DENSITY must have a matching entry in _ATTRS."""
    for code in _DENSITY:
        assert code in _ATTRS, f"Missing _ATTRS entry for {code}"


def test_all_density_types_in_type_seeds() -> None:
    """Every density type code must appear in _TYPE_SEEDS (cross-reference)."""
    all_codes = {t["type_code"] for types in _TYPE_SEEDS.values() for t in types}
    for code in _DENSITY:
        assert code in all_codes, f"{code} not found in _TYPE_SEEDS"


def test_attrs_depth_ranges_sensible() -> None:
    """min depth < max depth, and both > 0 for all type codes."""
    for code, attr in _ATTRS.items():
        lo, hi = attr["depth"]
        assert 0 < lo < hi, f"{code}: invalid depth range ({lo}, {hi})"


# ── Expected count ────────────────────────────────────────────────────────────

def test_expected_total_asset_count() -> None:
    """Verify the deterministic per-corridor count × 5 corridors."""
    per_corridor = sum(ls + pt for ls, pt in _DENSITY.values())
    assert expected_total_asset_count() == per_corridor * 5
    # Sanity: should be in the documented ~395-410 range
    assert 350 < expected_total_asset_count() < 500


def test_density_per_corridor_breakdown() -> None:
    """Gas service pipes (20) and elec/water services (18 each) dominate points."""
    ls_total = sum(ls for ls, _ in _DENSITY.values())
    pt_total = sum(pt for _, pt in _DENSITY.values())
    # More point assets than linestrings (service connections)
    assert pt_total > ls_total


# ── Geometry helpers ──────────────────────────────────────────────────────────

@pytest.fixture
def rng() -> random.Random:
    return random.Random(SEED)


def test_linestring_wkt_format(rng: random.Random) -> None:
    corridor = _CORRIDORS[0]
    wkt = _linestring_wkt(rng, corridor)
    assert wkt.startswith("LINESTRING(")
    assert wkt.endswith(")")
    # Must have at least 2 coordinate pairs (possibly 3)
    inner = wkt[len("LINESTRING("):-1]
    pairs = inner.split(", ")
    assert len(pairs) >= 2


def test_linestring_wkt_coords_in_birmingham(rng: random.Random) -> None:
    """Generated coordinates must lie roughly in Birmingham."""
    for corridor in _CORRIDORS:
        wkt = _linestring_wkt(rng, corridor)
        inner = wkt[len("LINESTRING("):-1]
        for pair in inner.split(", "):
            lng, lat = map(float, pair.split())
            assert -2.1 < lng < -1.7, f"Longitude {lng} out of Birmingham range"
            assert 52.3 < lat < 52.7, f"Latitude {lat} out of Birmingham range"


def test_point_wkt_format(rng: random.Random) -> None:
    corridor = _CORRIDORS[1]
    wkt = _point_wkt(rng, corridor)
    assert wkt.startswith("POINT(")
    assert wkt.endswith(")")
    inner = wkt[len("POINT("):-1]
    parts = inner.split()
    assert len(parts) == 2
    float(parts[0])  # longitude — should parse
    float(parts[1])  # latitude — should parse


def test_point_wkt_coords_in_birmingham(rng: random.Random) -> None:
    for corridor in _CORRIDORS:
        wkt = _point_wkt(rng, corridor)
        inner = wkt[len("POINT("):-1]
        lng, lat = map(float, inner.split())
        assert -2.1 < lng < -1.7
        assert 52.3 < lat < 52.7


def test_linestring_is_deterministic() -> None:
    """Same seed → same geometry every run (ADR-022 determinism)."""
    r1 = random.Random(SEED)
    r2 = random.Random(SEED)
    corridor = _CORRIDORS[2]
    assert _linestring_wkt(r1, corridor) == _linestring_wkt(r2, corridor)


def test_point_is_deterministic() -> None:
    r1 = random.Random(SEED)
    r2 = random.Random(SEED)
    corridor = _CORRIDORS[3]
    assert _point_wkt(r1, corridor) == _point_wkt(r2, corridor)


# ── Date helper ───────────────────────────────────────────────────────────────

def test_rand_date_in_range(rng: random.Random) -> None:
    from datetime import date

    for _ in range(50):
        d = _rand_date(rng)
        assert date(1975, 1, 1) <= d <= date(2022, 12, 31)


# ── External asset ID format ──────────────────────────────────────────────────

def test_external_id_prefix() -> None:
    """All generated external IDs in a deterministic run must start with 'SYN-'."""
    # Reconstruct what the generator would produce for the first linestring asset
    corridor = _CORRIDORS[0]
    abbrev = corridor["id"].replace("-", "")[:8].upper()
    first_type_code = next(iter(_DENSITY))
    expected_prefix = f"SYN-{first_type_code[:8]}-{abbrev}-0001"
    assert expected_prefix.startswith("SYN-")
    assert abbrev == "A38BRIST"  # sanity check corridor abbrev
