"""DT-008 — Tests for the synthetic D-TRO generator.

Strategy: pure-Python unit tests — no live database required.
Mirrors the pattern of test_nuar_synthetic.py.
"""
from __future__ import annotations

import random
import uuid
from datetime import date

import pytest

from services.synthetic.dtro_generator import (
    SEED,
    _DESCRIPTIONS,
    _PERMANENT_COUNT,
    _TEMPORARY_COUNT,
    _TRO_TYPE_WEIGHTS,
    _build_document,
    _build_restriction,
    _geometry_wkt,
    _load_authorities,
    _polygon_wkt,
    _linestring_wkt,
    _rand_date_past,
    _rand_ttro_dates,
    _wkt_to_geojson,
    expected_order_count,
    expected_permanent_count,
    expected_temporary_count,
)


# ── Constants ─────────────────────────────────────────────────────────────────

def test_seed_is_42() -> None:
    assert SEED == 42


def test_expected_order_count() -> None:
    assert expected_order_count() == _PERMANENT_COUNT + _TEMPORARY_COUNT


def test_permanent_count() -> None:
    assert expected_permanent_count() == 500


def test_temporary_count() -> None:
    assert expected_temporary_count() == 200


def test_tro_type_weights_sum_to_one() -> None:
    total = sum(w for _, w in _TRO_TYPE_WEIGHTS)
    assert abs(total - 1.0) < 0.001


def test_tro_types_all_have_descriptions() -> None:
    tro_types = {t for t, _ in _TRO_TYPE_WEIGHTS}
    for tro_type in tro_types:
        assert tro_type in _DESCRIPTIONS, f"Missing descriptions for {tro_type}"
        assert len(_DESCRIPTIONS[tro_type]) > 0


# ── Geometry helpers ──────────────────────────────────────────────────────────

@pytest.fixture
def rng() -> random.Random:
    return random.Random(SEED)


def test_linestring_wkt_format(rng: random.Random) -> None:
    wkt = _linestring_wkt(rng, -1.9, 52.48, 0.1, 0.005)
    assert wkt.startswith("LINESTRING(")
    assert wkt.endswith(")")


def test_polygon_wkt_format(rng: random.Random) -> None:
    wkt = _polygon_wkt(rng, -1.9, 52.48, 0.1)
    assert wkt.startswith("POLYGON((")
    assert wkt.endswith("))")


def test_geometry_wkt_zone_types_return_polygon(rng: random.Random) -> None:
    zone_types = ["parkingRestriction", "pedestrianZone", "busLane", "cycleLane"]
    for tro_type in zone_types:
        wkt = _geometry_wkt(rng, tro_type, -1.9, 52.48, 0.1)
        assert wkt.startswith("POLYGON"), f"{tro_type} should return Polygon, got {wkt[:20]}"


def test_geometry_wkt_linear_types_return_linestring(rng: random.Random) -> None:
    linear_types = ["speedLimit", "roadClosure", "weightRestriction", "oneWay"]
    for tro_type in linear_types:
        wkt = _geometry_wkt(rng, tro_type, -1.9, 52.48, 0.1)
        assert wkt.startswith("LINESTRING"), f"{tro_type} should return LineString, got {wkt[:20]}"


# ── Schema conformance ────────────────────────────────────────────────────────

def test_dtro_schema_conformance() -> None:
    """test_dtro_schema_conformance: generated document must have v4.0.0 fields."""
    rng = random.Random(SEED)
    authorities = _load_authorities()
    auth = authorities[0]
    tro_id = str(uuid.uuid4())
    doc, geom_wkt, speed_mph, restriction_type = _build_document(
        rng, tro_id, auth, "speedLimit", False,
        date(2020, 1, 1), None, 1
    )
    assert doc["schemaVersion"] == "4.0.0"
    assert "header" in doc
    assert "body" in doc
    assert "tro" in doc["body"]
    assert "provisions" in doc["body"]
    tro = doc["body"]["tro"]
    assert "referenceNumber" in tro
    assert "type" in tro
    assert "authority" in tro
    assert "validFrom" in tro


def test_dtro_determinism() -> None:
    """test_dtro_determinism: same seed → identical first document."""
    rng1 = random.Random(SEED)
    rng2 = random.Random(SEED)
    authorities = _load_authorities()
    auth = authorities[1]
    tro_id = "fixed-id"
    doc1, _, _, _ = _build_document(rng1, tro_id, auth, "roadClosure", True, date(2026, 6, 1), date(2026, 6, 30), 1)
    doc2, _, _, _ = _build_document(rng2, tro_id, auth, "roadClosure", True, date(2026, 6, 1), date(2026, 6, 30), 1)
    assert doc1 == doc2


def test_dtro_tro_types_distribution() -> None:
    """test_dtro_tro_types_distribution: speedLimit must be most common type."""
    rng = random.Random(SEED)
    authorities = _load_authorities()
    tro_types = [t for t, _ in _TRO_TYPE_WEIGHTS]
    type_weights = [w for _, w in _TRO_TYPE_WEIGHTS]
    counts: dict[str, int] = {}
    for _ in range(200):
        t = rng.choices(tro_types, weights=type_weights)[0]
        counts[t] = counts.get(t, 0) + 1
    assert counts.get("speedLimit", 0) > counts.get("pedestrianZone", 0)


def test_dtro_ttro_has_expiry_date() -> None:
    """test_dtro_ttro_has_expiry_date: temporary TROs must always have valid_to."""
    rng = random.Random(SEED)
    for _ in range(20):
        start, end = _rand_ttro_dates(rng)
        assert end is not None
        assert end > start


def test_dtro_geometry_wgs84() -> None:
    """test_dtro_geometry_wgs84: all generated coordinates must be valid WGS84."""
    rng = random.Random(SEED)
    authorities = _load_authorities()
    for auth in authorities[:5]:
        cx, cy = auth["approxBboxCentre"]
        radius = auth["approxBboxRadius"]
        wkt = _linestring_wkt(rng, cx, cy, radius, 0.005)
        inner = wkt[len("LINESTRING("):-1]
        for pair in inner.split(", "):
            lng, lat = map(float, pair.split())
            assert -180 <= lng <= 180, f"Invalid longitude: {lng}"
            assert -90 <= lat <= 90, f"Invalid latitude: {lat}"


def test_dtro_authority_coverage() -> None:
    """test_dtro_authority_coverage: authorities.json must have >= 40 entries."""
    authorities = _load_authorities()
    assert len(authorities) >= 40


def test_dtro_speed_limit_values() -> None:
    """test_dtro_speed_limit_values: speed limits must be from the valid set."""
    valid_speeds = {20, 30, 40, 50, 60, 70}
    rng = random.Random(SEED)
    for _ in range(50):
        restriction = _build_restriction(rng, "speedLimit")
        assert restriction["speedInMph"] in valid_speeds


def test_dtro_cli_generates_fixture(tmp_path) -> None:
    """test_dtro_cli_generates_fixture: CLI script produces valid JSON file."""
    import json
    from scripts.generate_dtro_fixtures import main
    output_file = tmp_path / "test_dtros.json"
    main(["--output", str(output_file), "--seed", "42", "--permanent", "5", "--temporary", "3"])
    assert output_file.exists()
    data = json.loads(output_file.read_text())
    assert len(data) == 8
    assert all(d["schemaVersion"] == "4.0.0" for d in data)
    assert all("body" in d for d in data)


# ── WKT to GeoJSON ───────────────────────────────────────────────────────────

def test_wkt_to_geojson_linestring() -> None:
    geojson = _wkt_to_geojson("LINESTRING(-1.9 52.48, -1.89 52.49)")
    assert geojson["type"] == "LineString"
    assert len(geojson["coordinates"]) == 2


def test_wkt_to_geojson_polygon() -> None:
    geojson = _wkt_to_geojson("POLYGON((-1.9 52.48, -1.89 52.48, -1.89 52.49, -1.9 52.49, -1.9 52.48))")
    assert geojson["type"] == "Polygon"
    assert len(geojson["coordinates"][0]) == 5
