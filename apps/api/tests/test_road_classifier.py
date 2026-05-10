"""Tests for SM-004: road classifier via OS Open Roads."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from schemas.domain import LineStringGeometry, PointGeometry, RoadInfo
from services.road_classifier import (
    RoadClassifier,
    _geometry_bbox,
    _parse_road_features,
    _representative_point,
)


# ── geometry helpers ───────────────────────────────────────────────────────────

def test_representative_point_from_point() -> None:
    geo = PointGeometry(type="Point", coordinates=(-1.8979, 52.4862))
    lon, lat = _representative_point(geo)
    assert lon == -1.8979
    assert lat == 52.4862


def test_representative_point_from_linestring_picks_midpoint() -> None:
    geo = LineStringGeometry(
        type="LineString",
        coordinates=[(-1.5, 53.8), (-1.51, 53.81), (-1.52, 53.82)],
    )
    lon, lat = _representative_point(geo)
    assert lon == -1.51
    assert lat == 53.81


def test_geometry_bbox_from_point() -> None:
    geo = PointGeometry(type="Point", coordinates=(-1.9, 52.5))
    min_lon, min_lat, max_lon, max_lat = _geometry_bbox(geo, buffer=0.001)
    assert abs(min_lon - (-1.901)) < 1e-9
    assert abs(max_lon - (-1.899)) < 1e-9
    assert abs(min_lat - 52.499) < 1e-9
    assert abs(max_lat - 52.501) < 1e-9


def test_geometry_bbox_from_linestring_spans_all_coords() -> None:
    geo = LineStringGeometry(
        type="LineString",
        coordinates=[(-1.5, 53.8), (-1.6, 53.9), (-1.55, 53.85)],
    )
    min_lon, min_lat, max_lon, max_lat = _geometry_bbox(geo, buffer=0.0)
    assert min_lon == -1.6
    assert max_lon == -1.5
    assert min_lat == 53.8
    assert max_lat == 53.9


# ── _parse_road_features ───────────────────────────────────────────────────────

def _feature(classification: str, function: str | None = None, name: str | None = None, form: str | None = None) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "roadClassification": classification,
            "roadFunction": function,
            "name1": name,
            "formOfWay": form,
        },
    }


def _collection(*features: dict) -> dict:
    return {"type": "FeatureCollection", "features": list(features)}


def test_parse_road_features_empty_returns_none() -> None:
    assert _parse_road_features({"type": "FeatureCollection", "features": []}) is None


def test_parse_road_features_missing_features_key() -> None:
    assert _parse_road_features({"type": "FeatureCollection"}) is None


def test_parse_road_features_a_road() -> None:
    payload = _collection(_feature("A Road", function="A Road", name="A38", form="Single Carriageway"))
    result = _parse_road_features(payload)
    assert result is not None
    assert result.road_classification == "A Road"
    assert result.road_name == "A38"
    assert result.form_of_way == "Single Carriageway"
    assert result.is_primary_route is True


def test_parse_road_features_motorway_is_primary() -> None:
    payload = _collection(_feature("Motorway", name="M6", form="Dual Carriageway"))
    result = _parse_road_features(payload)
    assert result is not None
    assert result.road_classification == "Motorway"
    assert result.is_primary_route is True


def test_parse_road_features_b_road_not_primary() -> None:
    payload = _collection(_feature("B Road", name="B4140"))
    result = _parse_road_features(payload)
    assert result is not None
    assert result.road_classification == "B Road"
    assert result.is_primary_route is False


def test_parse_road_features_unclassified_not_primary() -> None:
    payload = _collection(_feature("Unclassified"))
    result = _parse_road_features(payload)
    assert result is not None
    assert result.road_classification == "Unclassified"
    assert result.is_primary_route is False


def test_parse_road_features_priority_sorting_motorway_wins() -> None:
    payload = _collection(
        _feature("B Road", name="B100"),
        _feature("Motorway", name="M42"),
        _feature("A Road", name="A45"),
    )
    result = _parse_road_features(payload)
    assert result is not None
    assert result.road_classification == "Motorway"
    assert result.road_name == "M42"


def test_parse_road_features_priority_sorting_a_road_beats_b_road() -> None:
    payload = _collection(
        _feature("B Road", name="B200"),
        _feature("Unclassified"),
        _feature("A Road", name="A38"),
    )
    result = _parse_road_features(payload)
    assert result is not None
    assert result.road_classification == "A Road"
    assert result.road_name == "A38"


def test_parse_road_features_no_classification_defaults() -> None:
    payload = _collection({"type": "Feature", "properties": {}})
    result = _parse_road_features(payload)
    assert result is not None
    assert result.road_classification == "Not Classified"
    assert result.is_primary_route is False


# ── RoadClassifier fixtures ────────────────────────────────────────────────────

@pytest.fixture
def mock_redis() -> AsyncMock:
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.set = AsyncMock()
    return r


@pytest.fixture
def mock_http() -> MagicMock:
    return MagicMock(spec=httpx.AsyncClient)


_POINT_GEO = PointGeometry(type="Point", coordinates=(-1.8979, 52.4862))

_SAMPLE_COLLECTION = _collection(
    _feature("A Road", function="A Road", name="A38", form="Single Carriageway")
)


def _ok_response(body: dict) -> MagicMock:
    r = MagicMock(spec=httpx.Response)
    r.status_code = 200
    r.json.return_value = body
    r.raise_for_status = MagicMock()
    return r


def _error_response(status_code: int) -> MagicMock:
    r = MagicMock(spec=httpx.Response)
    r.status_code = status_code
    r.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=MagicMock(spec=httpx.Request),
            response=r,
        )
    )
    return r


# ── RoadClassifier.classify_by_usrn ───────────────────────────────────────────

async def test_classify_no_api_key_returns_none(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    with patch("services.road_classifier.settings") as s:
        s.os_api_key = ""
        classifier = RoadClassifier(mock_redis, mock_http)
        result = await classifier.classify_by_usrn("41507223", _POINT_GEO)

    assert result is None
    mock_http.get.assert_not_called()


async def test_classify_cache_hit(mock_redis: AsyncMock, mock_http: MagicMock) -> None:
    cached = RoadInfo(
        road_classification="A Road",
        road_name="A38",
        form_of_way="Single Carriageway",
        is_primary_route=True,
    )
    mock_redis.get = AsyncMock(return_value=cached.model_dump_json())

    with patch("services.road_classifier.settings") as s:
        s.os_api_key = "test-key"
        classifier = RoadClassifier(mock_redis, mock_http)
        result = await classifier.classify_by_usrn("41507223", _POINT_GEO)

    assert result is not None
    assert result.road_classification == "A Road"
    assert result.is_primary_route is True
    mock_http.get.assert_not_called()


async def test_classify_cache_miss_calls_api_and_caches(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    mock_http.get = AsyncMock(return_value=_ok_response(_SAMPLE_COLLECTION))

    with patch("services.road_classifier.settings") as s:
        s.os_api_key = "os-key-xyz"
        classifier = RoadClassifier(mock_redis, mock_http)
        result = await classifier.classify_by_usrn("41507223", _POINT_GEO)

    assert result is not None
    assert result.road_classification == "A Road"

    mock_http.get.assert_called_once()
    call_params = mock_http.get.call_args.kwargs["params"]
    assert "bbox" in call_params
    assert call_params["key"] == "os-key-xyz"

    # Must be written to cache with a TTL
    mock_redis.set.assert_called_once()
    _, cached_value = mock_redis.set.call_args.args
    assert "A Road" in cached_value
    assert mock_redis.set.call_args.kwargs.get("ex") == 86_400


async def test_classify_404_returns_none(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    r = MagicMock(spec=httpx.Response)
    r.status_code = 404
    mock_http.get = AsyncMock(return_value=r)

    with patch("services.road_classifier.settings") as s:
        s.os_api_key = "test-key"
        classifier = RoadClassifier(mock_redis, mock_http)
        result = await classifier.classify_by_usrn("00000000", _POINT_GEO)

    assert result is None
    mock_redis.set.assert_not_called()


async def test_classify_empty_features_returns_none(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    mock_http.get = AsyncMock(
        return_value=_ok_response({"type": "FeatureCollection", "features": []})
    )

    with patch("services.road_classifier.settings") as s:
        s.os_api_key = "test-key"
        classifier = RoadClassifier(mock_redis, mock_http)
        result = await classifier.classify_by_usrn("41507223", _POINT_GEO)

    assert result is None
    mock_redis.set.assert_not_called()


async def test_classify_linestring_geometry(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    line_geo = LineStringGeometry(
        type="LineString",
        coordinates=[(-1.5, 53.8), (-1.51, 53.81), (-1.52, 53.82)],
    )
    mock_http.get = AsyncMock(
        return_value=_ok_response(_collection(_feature("B Road", name="B4140")))
    )

    with patch("services.road_classifier.settings") as s:
        s.os_api_key = "test-key"
        classifier = RoadClassifier(mock_redis, mock_http)
        result = await classifier.classify_by_usrn("12345", line_geo)

    assert result is not None
    assert result.road_classification == "B Road"
    assert result.is_primary_route is False
