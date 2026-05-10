"""Tests for SM-002: works_repository conversion logic.

These tests cover the domain <-> DB row conversion functions and
the geometry helper functions — the parts that don't need a live
PostgreSQL connection. Integration tests (real upsert/query against
PostGIS) are added in SM-006 when the query endpoints are built.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from schemas.domain import LineStringGeometry, PointGeometry, StreetWork
from services.works_repository import (
    _domain_to_values,
    _geometry_to_wkt,
    _row_to_domain,
    _to_date,
    _to_datetime,
)


# ── Date helpers ───────────────────────────────────────────────────────────────

def test_to_date_iso_string() -> None:
    assert _to_date("2025-06-01") == date(2025, 6, 1)


def test_to_date_datetime_prefix() -> None:
    # SM API sometimes returns full datetime strings for date fields
    assert _to_date("2025-06-01T10:00:00Z") == date(2025, 6, 1)


def test_to_date_none() -> None:
    assert _to_date(None) is None
    assert _to_date("") is None


def test_to_datetime_utc_z() -> None:
    dt = _to_datetime("2025-06-01T10:00:00Z")
    assert dt is not None
    assert dt.year == 2025
    assert dt.month == 6
    assert dt.tzinfo is not None


def test_to_datetime_none() -> None:
    assert _to_datetime(None) is None


# ── Geometry helpers ───────────────────────────────────────────────────────────

def test_geometry_to_wkt_point() -> None:
    geo = PointGeometry(type="Point", coordinates=(-1.8979, 52.4862))
    wkt_el = _geometry_to_wkt(geo)
    assert "POINT" in wkt_el.data
    assert "-1.8979" in wkt_el.data
    assert "52.4862" in wkt_el.data
    assert wkt_el.srid == 4326


def test_geometry_to_wkt_linestring() -> None:
    geo = LineStringGeometry(
        type="LineString",
        coordinates=[(-1.5, 53.8), (-1.51, 53.81), (-1.52, 53.82)],
    )
    wkt_el = _geometry_to_wkt(geo)
    assert "LINESTRING" in wkt_el.data
    assert wkt_el.srid == 4326
    assert wkt_el.data.count(",") == 2  # two commas = three coordinate pairs


# ── domain_to_values ───────────────────────────────────────────────────────────

def _sample_work(**overrides) -> StreetWork:
    base = dict(
        permit_reference="WG7/2025/04001234",
        usrn="41507223",
        street_name="Corporation Street",
        authority="Birmingham City Council",
        promoter="Cadent Gas",
        promoter_licence_number="WG7",
        work_type="Standard",
        traffic_management_type="Two-way signals",
        restriction_type="Lane closure",
        proposed_start_date="2025-06-01",
        proposed_end_date="2025-06-07",
        status="granted",
        geometry=PointGeometry(type="Point", coordinates=(-1.8979, 52.4862)),
    )
    base.update(overrides)
    return StreetWork(**base)


def test_domain_to_values_maps_all_fields() -> None:
    work = _sample_work()
    values = _domain_to_values(work)

    assert values["permit_reference"] == "WG7/2025/04001234"
    assert values["usrn"] == "41507223"
    assert values["authority"] == "Birmingham City Council"
    assert values["status"] == "granted"
    assert values["proposed_start_date"] == date(2025, 6, 1)
    assert values["proposed_end_date"] == date(2025, 6, 7)
    assert values["actual_start_date"] is None
    assert values["actual_end_date"] is None
    assert values["risk_score"] is None

    # Geometry should be a WKTElement
    from geoalchemy2.elements import WKTElement
    assert isinstance(values["geometry"], WKTElement)
    assert values["geometry"].srid == 4326


def test_domain_to_values_with_actual_dates() -> None:
    work = _sample_work(
        actual_start_date="2025-06-01T08:30:00Z",
        actual_end_date="2025-06-07T16:00:00Z",
    )
    values = _domain_to_values(work)
    assert values["actual_start_date"] is not None
    assert values["actual_end_date"] is not None


def test_domain_to_values_raises_on_missing_dates() -> None:
    work = _sample_work(proposed_start_date="", proposed_end_date="")
    with pytest.raises(ValueError, match="invalid date"):
        _domain_to_values(work)


# ── row_to_domain ──────────────────────────────────────────────────────────────

def test_row_to_domain_point_geometry() -> None:
    from shapely.geometry import Point as ShapelyPoint
    from geoalchemy2.shape import from_shape

    mock_row = MagicMock()
    mock_row.permit_reference = "WG7/2025/04001234"
    mock_row.usrn = "41507223"
    mock_row.street_name = "Corporation Street"
    mock_row.authority = "Birmingham City Council"
    mock_row.promoter = "Cadent Gas"
    mock_row.promoter_licence_number = "WG7"
    mock_row.work_type = "Standard"
    mock_row.traffic_management_type = "Two-way signals"
    mock_row.restriction_type = "Lane closure"
    mock_row.proposed_start_date = date(2025, 6, 1)
    mock_row.proposed_end_date = date(2025, 6, 7)
    mock_row.actual_start_date = None
    mock_row.actual_end_date = None
    mock_row.status = "granted"
    mock_row.risk_score = None
    mock_row.geometry = from_shape(ShapelyPoint(-1.8979, 52.4862), srid=4326)

    work = _row_to_domain(mock_row)

    assert work.permit_reference == "WG7/2025/04001234"
    assert work.status == "granted"
    assert isinstance(work.geometry, PointGeometry)
    assert abs(work.geometry.coordinates[0] - (-1.8979)) < 1e-4
    assert abs(work.geometry.coordinates[1] - 52.4862) < 1e-4


def test_row_to_domain_linestring_geometry() -> None:
    from shapely.geometry import LineString as ShapelyLine
    from geoalchemy2.shape import from_shape

    mock_row = MagicMock()
    mock_row.permit_reference = "AB/2025/00001"
    mock_row.usrn = "12345"
    mock_row.street_name = "Main Road"
    mock_row.authority = "Test Council"
    mock_row.promoter = "Test Co"
    mock_row.promoter_licence_number = "AB"
    mock_row.work_type = "Major"
    mock_row.traffic_management_type = "Road closure"
    mock_row.restriction_type = "Full closure"
    mock_row.proposed_start_date = date(2025, 7, 1)
    mock_row.proposed_end_date = date(2025, 7, 14)
    mock_row.actual_start_date = None
    mock_row.actual_end_date = None
    mock_row.status = "in_progress"
    mock_row.risk_score = None
    mock_row.geometry = from_shape(
        ShapelyLine([(-1.5, 53.8), (-1.51, 53.81), (-1.52, 53.82)]), srid=4326
    )

    work = _row_to_domain(mock_row)

    assert isinstance(work.geometry, LineStringGeometry)
    assert len(work.geometry.coordinates) == 3


# ── upsert_work ────────────────────────────────────────────────────────────────

async def test_upsert_work_executes_and_commits() -> None:
    from services.works_repository import upsert_work

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    work = _sample_work()
    await upsert_work(mock_session, work)

    mock_session.execute.assert_called_once()
    mock_session.commit.assert_called_once()
