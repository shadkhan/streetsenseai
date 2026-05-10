"""Tests for SM-003: USRN resolver via OS NSG API."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from schemas.domain import USRNInfo
from services.usrn_resolver import USRNResolver, _parse_nsg_response


# ── _parse_nsg_response ────────────────────────────────────────────────────────

def test_parse_nsg_response_complete() -> None:
    payload = {
        "header": {"totalresults": 1},
        "results": [
            {
                "STREET_DESCRIPTOR": {
                    "USRN": "41507223",
                    "STREET_DESCRIPTION": "CORPORATION STREET",
                    "LOCALITY_NAME": "CITY CENTRE",
                    "TOWN_NAME": "BIRMINGHAM",
                    "ADMINISTRATIVE_AREA": "BIRMINGHAM",
                },
                "STREET": {
                    "USRN": "41507223",
                    "CLASSIFICATION": "B",
                },
            }
        ],
    }
    result = _parse_nsg_response(payload)
    assert result is not None
    assert result.usrn == "41507223"
    assert result.street_name == "Corporation Street"  # title-cased
    assert result.locality == "CITY CENTRE"
    assert result.town == "BIRMINGHAM"
    assert result.authority == "BIRMINGHAM"
    assert result.road_classification == "B"


def test_parse_nsg_response_empty_results() -> None:
    assert _parse_nsg_response({"results": []}) is None


def test_parse_nsg_response_missing_results_key() -> None:
    assert _parse_nsg_response({}) is None


def test_parse_nsg_response_missing_usrn() -> None:
    payload = {
        "results": [
            {
                "STREET_DESCRIPTOR": {
                    "STREET_DESCRIPTION": "HIGH STREET",
                    "TOWN_NAME": "LONDON",
                },
                "STREET": {},
            }
        ]
    }
    assert _parse_nsg_response(payload) is None


def test_parse_nsg_response_missing_street_description() -> None:
    payload = {
        "results": [
            {
                "STREET_DESCRIPTOR": {
                    "USRN": "99999",
                },
                "STREET": {"USRN": "99999"},
            }
        ]
    }
    assert _parse_nsg_response(payload) is None


def test_parse_nsg_response_optional_fields_absent() -> None:
    payload = {
        "results": [
            {
                "STREET_DESCRIPTOR": {
                    "USRN": "12345",
                    "STREET_DESCRIPTION": "UNNAMED TRACK",
                },
                "STREET": {"USRN": "12345"},
            }
        ]
    }
    result = _parse_nsg_response(payload)
    assert result is not None
    assert result.usrn == "12345"
    assert result.locality is None
    assert result.town is None
    assert result.authority is None
    assert result.road_classification is None


def test_parse_nsg_response_a_road_classification() -> None:
    payload = {
        "results": [
            {
                "STREET_DESCRIPTOR": {
                    "USRN": "10023456",
                    "STREET_DESCRIPTION": "A38 BRISTOL ROAD",
                    "TOWN_NAME": "BIRMINGHAM",
                    "ADMINISTRATIVE_AREA": "BIRMINGHAM",
                },
                "STREET": {"USRN": "10023456", "CLASSIFICATION": "A"},
            }
        ]
    }
    result = _parse_nsg_response(payload)
    assert result is not None
    assert result.road_classification == "A"
    assert result.street_name == "A38 Bristol Road"


def test_parse_nsg_response_title_case_applied() -> None:
    payload = {
        "results": [
            {
                "STREET_DESCRIPTOR": {
                    "USRN": "777",
                    "STREET_DESCRIPTION": "THE BULL RING",
                    "TOWN_NAME": "BIRMINGHAM",
                    "ADMINISTRATIVE_AREA": "BIRMINGHAM",
                },
                "STREET": {},
            }
        ]
    }
    result = _parse_nsg_response(payload)
    assert result is not None
    assert result.street_name == "The Bull Ring"


# ── USRNResolver fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def mock_redis() -> AsyncMock:
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)  # cache miss by default
    r.set = AsyncMock()
    return r


@pytest.fixture
def mock_http() -> MagicMock:
    return MagicMock(spec=httpx.AsyncClient)


_SAMPLE_NSG_RESPONSE = {
    "header": {"totalresults": 1},
    "results": [
        {
            "STREET_DESCRIPTOR": {
                "USRN": "41507223",
                "STREET_DESCRIPTION": "CORPORATION STREET",
                "LOCALITY_NAME": "CITY CENTRE",
                "TOWN_NAME": "BIRMINGHAM",
                "ADMINISTRATIVE_AREA": "BIRMINGHAM",
            },
            "STREET": {"USRN": "41507223", "CLASSIFICATION": "B"},
        }
    ],
}


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


# ── USRNResolver.resolve ───────────────────────────────────────────────────────

async def test_resolve_returns_none_when_no_api_key(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    with patch("services.usrn_resolver.settings") as s:
        s.os_api_key = ""
        resolver = USRNResolver(mock_redis, mock_http)
        result = await resolver.resolve("41507223")

    assert result is None
    mock_http.get.assert_not_called()


async def test_resolve_cache_hit(mock_redis: AsyncMock, mock_http: MagicMock) -> None:
    info = USRNInfo(
        usrn="41507223",
        street_name="Corporation Street",
        town="BIRMINGHAM",
        authority="BIRMINGHAM",
        road_classification="B",
    )
    mock_redis.get = AsyncMock(return_value=info.model_dump_json())

    with patch("services.usrn_resolver.settings") as s:
        s.os_api_key = "test-key"
        resolver = USRNResolver(mock_redis, mock_http)
        result = await resolver.resolve("41507223")

    assert result is not None
    assert result.usrn == "41507223"
    assert result.street_name == "Corporation Street"
    mock_http.get.assert_not_called()  # served from cache, no API call


async def test_resolve_cache_miss_hits_api_and_caches(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    mock_http.get = AsyncMock(return_value=_ok_response(_SAMPLE_NSG_RESPONSE))

    with patch("services.usrn_resolver.settings") as s:
        s.os_api_key = "os-key-123"
        resolver = USRNResolver(mock_redis, mock_http)
        result = await resolver.resolve("41507223")

    assert result is not None
    assert result.street_name == "Corporation Street"
    assert result.road_classification == "B"

    # Verify API was called with correct params
    mock_http.get.assert_called_once()
    call_kwargs = mock_http.get.call_args
    assert "usrn" in call_kwargs.kwargs.get("params", {}) or "41507223" in str(call_kwargs)

    # Verify result was written to cache with no TTL
    mock_redis.set.assert_called_once()
    cache_key, cached_value = mock_redis.set.call_args.args
    assert "41507223" in cache_key
    assert "Corporation Street" in cached_value


async def test_resolve_404_returns_none(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    r = MagicMock(spec=httpx.Response)
    r.status_code = 404
    mock_http.get = AsyncMock(return_value=r)

    with patch("services.usrn_resolver.settings") as s:
        s.os_api_key = "test-key"
        resolver = USRNResolver(mock_redis, mock_http)
        result = await resolver.resolve("00000000")

    assert result is None
    mock_redis.set.assert_not_called()


async def test_resolve_empty_results_returns_none(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    mock_http.get = AsyncMock(
        return_value=_ok_response({"header": {"totalresults": 0}, "results": []})
    )

    with patch("services.usrn_resolver.settings") as s:
        s.os_api_key = "test-key"
        resolver = USRNResolver(mock_redis, mock_http)
        result = await resolver.resolve("41507223")

    assert result is None
    mock_redis.set.assert_not_called()


# ── USRNResolver.batch_resolve ─────────────────────────────────────────────────

async def test_batch_resolve_returns_successful_usrns(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    good_response = _ok_response(_SAMPLE_NSG_RESPONSE)
    not_found = MagicMock(spec=httpx.Response)
    not_found.status_code = 404

    # First USRN found, second not found
    mock_http.get = AsyncMock(side_effect=[good_response, not_found])

    with patch("services.usrn_resolver.settings") as s:
        s.os_api_key = "test-key"
        resolver = USRNResolver(mock_redis, mock_http)
        results = await resolver.batch_resolve(["41507223", "00000000"])

    assert "41507223" in results
    assert "00000000" not in results
    assert len(results) == 1


async def test_batch_resolve_empty_list(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    with patch("services.usrn_resolver.settings") as s:
        s.os_api_key = "test-key"
        resolver = USRNResolver(mock_redis, mock_http)
        results = await resolver.batch_resolve([])

    assert results == {}
    mock_http.get.assert_not_called()
