"""DT-002 — Tests for the permit+TRO conflict detector.

Strategy: pure-Python unit tests — no database required.
Uses synthetic StreetWork and D-TRO v4.0.0 document dicts.
"""
from __future__ import annotations

from datetime import date

import pytest

from schemas.domain import LineStringGeometry, PointGeometry, StreetWork
from services.conflict_detector import (
    ConflictDetector,
    _dates_overlap,
    _geometry_approx_intersects,
    _plain_english_description,
)


# ── Test helpers ──────────────────────────────────────────────────────────────

def _make_permit(
    ref: str = "TEST/2026/001",
    street: str = "Test Street",
    start: str = "2026-06-01",
    end: str = "2026-06-30",
    lng: float = -1.9,
    lat: float = 52.48,
) -> StreetWork:
    return StreetWork(
        permitReference=ref,
        usrn="41507223",
        streetName=street,
        authority="Birmingham City Council",
        promoter="Test Promoter",
        promoterLicenceNumber="PL-001",
        workType="utility",
        trafficManagementType="traffic_management",
        restrictionType="road_closure",
        proposedStartDate=start,
        proposedEndDate=end,
        status="in_progress",
        geometry=PointGeometry(type="Point", coordinates=[lng, lat]),
    )


def _make_dtro_doc(
    tro_type: str = "speedLimit",
    valid_from: str = "2020-01-01",
    valid_to: str | None = None,
    authority: str = "Birmingham City Council",
    lng: float = -1.9,
    lat: float = 52.48,
) -> dict:
    tro_id = f"syn-{tro_type}-001"
    ref = f"TRO/BCC/2020/001"
    return {
        "id": tro_id,
        "schemaVersion": "4.0.0",
        "header": {"notice": "TRO", "source": {"reference": ref, "publisher": authority, "provenance": "synthetic", "timestamp": valid_from}},
        "body": {
            "tro": {
                "referenceNumber": ref,
                "type": tro_type,
                "description": f"Test {tro_type}",
                "authority": authority,
                "isTemporary": valid_to is not None,
                "validFrom": valid_from,
                "validTo": valid_to,
            },
            "provisions": [
                {
                    "id": "prov-001",
                    "referenceNumber": f"{ref}-P001",
                    "type": tro_type,
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[lng - 0.005, lat], [lng + 0.005, lat]],
                    },
                    "restriction": {"speedInMph": 30 if tro_type == "speedLimit" else None},
                }
            ],
        },
    }


# ── Date overlap tests ────────────────────────────────────────────────────────

def test_conflict_temporal_no_spatial() -> None:
    """test_conflict_temporal_no_spatial: temporal overlap with non-overlapping geometry."""
    permit = _make_permit(start="2026-06-01", end="2026-06-30", lng=-1.9, lat=52.48)
    # TRO geometry far away (different city)
    doc = _make_dtro_doc(valid_from="2026-05-01", valid_to="2026-07-31", lng=-0.12, lat=51.5)
    detector = ConflictDetector()
    results = detector.detect_permit_tro_conflicts(permit, [doc])
    # Should detect temporal overlap but no spatial overlap
    temp_results = [r for r in results if r.conflict_type == "temporal_overlap"]
    assert len(temp_results) == 1


def test_conflict_spatial_overlap() -> None:
    """test_conflict_spatial_overlap: permit near TRO geometry but outside time window."""
    permit = _make_permit(start="2030-01-01", end="2030-12-31", lng=-1.9, lat=52.48)
    doc = _make_dtro_doc(valid_from="2020-01-01", valid_to="2025-12-31", lng=-1.9, lat=52.48)
    detector = ConflictDetector()
    results = detector.detect_permit_tro_conflicts(permit, [doc])
    spatial_results = [r for r in results if r.conflict_type == "spatial_overlap"]
    assert len(spatial_results) == 1


def test_conflict_both_dimensions() -> None:
    """test_conflict_both_dimensions: overlapping in both space and time."""
    permit = _make_permit(start="2026-06-01", end="2026-06-30", lng=-1.9, lat=52.48)
    doc = _make_dtro_doc(
        tro_type="roadClosure",
        valid_from="2026-05-01",
        valid_to="2026-07-31",
        lng=-1.9, lat=52.48,
    )
    detector = ConflictDetector()
    results = detector.detect_permit_tro_conflicts(permit, [doc])
    assert len(results) == 1
    assert results[0].conflict_type == "both"


def test_conflict_no_conflict() -> None:
    """test_conflict_no_conflict: no overlap in space or time."""
    permit = _make_permit(start="2026-06-01", end="2026-06-30", lng=-1.9, lat=52.48)
    # TRO far away AND in the past
    doc = _make_dtro_doc(valid_from="2010-01-01", valid_to="2015-12-31", lng=0.0, lat=51.5)
    detector = ConflictDetector()
    results = detector.detect_permit_tro_conflicts(permit, [doc])
    assert len(results) == 0


def test_conflict_severity_classification() -> None:
    """test_conflict_severity_classification: roadClosure → critical, speedLimit → low."""
    permit = _make_permit(start="2026-06-01", end="2026-06-30", lng=-1.9, lat=52.48)

    closure_doc = _make_dtro_doc("roadClosure", "2026-05-01", "2026-07-31", lng=-1.9, lat=52.48)
    speed_doc = _make_dtro_doc("speedLimit", "2026-05-01", valid_to=None, lng=-1.9, lat=52.48)

    detector = ConflictDetector()
    closure_results = detector.detect_permit_tro_conflicts(permit, [closure_doc])
    speed_results = detector.detect_permit_tro_conflicts(permit, [speed_doc])

    assert closure_results[0].severity == "critical"
    assert speed_results[0].severity == "low"


def test_corridor_conflicts_endpoint() -> None:
    """test_corridor_conflicts_endpoint: detect_corridor_conflicts deduplicates permits."""
    permit_a = _make_permit("A/2026/001", start="2026-06-01", end="2026-06-30", lng=-1.9, lat=52.48)
    permit_b = _make_permit("B/2026/002", start="2026-06-15", end="2026-07-15", lng=-1.9, lat=52.48)
    doc = _make_dtro_doc("busLane", "2026-05-01", "2026-08-01", lng=-1.9, lat=52.48)

    detector = ConflictDetector()
    results = detector.detect_corridor_conflicts([permit_a, permit_b], [doc])
    # Both permits conflict — 2 results (no dedup across different permits)
    refs = {r.permit_reference for r in results}
    assert "A/2026/001" in refs
    assert "B/2026/002" in refs


def test_conflict_description_not_empty() -> None:
    """test_conflict_description_not_empty: description is always a non-empty string."""
    permit = _make_permit()
    tro_types = ["speedLimit", "roadClosure", "parkingRestriction", "busLane", "weightRestriction"]
    for tro_type in tro_types:
        desc = _plain_english_description(tro_type, permit, "both", "TRO/REF/001")
        assert desc and len(desc) > 10, f"Empty description for {tro_type}"


def test_conflict_detector_handles_empty_dtros() -> None:
    """test_conflict_detector_handles_empty_dtros: empty list → no conflicts."""
    permit = _make_permit()
    detector = ConflictDetector()
    results = detector.detect_permit_tro_conflicts(permit, [])
    assert results == []
