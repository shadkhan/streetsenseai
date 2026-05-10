"""Tests for SM-006: works query endpoints."""
from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from database import get_db
from schemas.domain import LineStringGeometry, PointGeometry, StreetWork


# ── Test fixtures ──────────────────────────────────────────────────────────────

def _sample_work(
    permit: str = "WG7/2025/04001234",
    status: str = "granted",
    usrn: str = "41507223",
    authority: str = "Birmingham City Council",
) -> StreetWork:
    return StreetWork(
        permit_reference=permit,
        usrn=usrn,
        street_name="Corporation Street",
        authority=authority,
        promoter="Cadent Gas",
        promoter_licence_number="WG7",
        work_type="Standard",
        traffic_management_type="Two-way signals",
        restriction_type="Lane closure",
        proposed_start_date="2025-06-01",
        proposed_end_date="2025-06-07",
        status=status,  # type: ignore[arg-type]
        geometry=PointGeometry(type="Point", coordinates=(-1.8979, 52.4862)),
    )


@pytest.fixture(autouse=True)
def override_db():
    """Replace the get_db dependency with a no-op async mock for all tests."""
    mock_session = AsyncMock()

    async def _mock_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _mock_get_db
    yield mock_session
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── GET /works/permit/{ref} ────────────────────────────────────────────────────

def test_get_permit_returns_camel_case_json(client: TestClient) -> None:
    work = _sample_work()
    with patch("routers.works.get_work_by_permit", AsyncMock(return_value=work)):
        resp = client.get("/works/permit/WG7/2025/04001234")

    assert resp.status_code == 200
    body = resp.json()
    # Verify camelCase serialisation
    assert body["permitReference"] == "WG7/2025/04001234"
    assert body["streetName"] == "Corporation Street"
    assert body["proposedStartDate"] == "2025-06-01"
    assert body["promoterLicenceNumber"] == "WG7"
    assert body["trafficManagementType"] == "Two-way signals"
    # No snake_case leakage
    assert "permit_reference" not in body
    assert "street_name" not in body


def test_get_permit_geometry_serialised(client: TestClient) -> None:
    work = _sample_work()
    with patch("routers.works.get_work_by_permit", AsyncMock(return_value=work)):
        resp = client.get("/works/permit/WG7/2025/04001234")

    geo = resp.json()["geometry"]
    assert geo["type"] == "Point"
    assert len(geo["coordinates"]) == 2


def test_get_permit_handles_slashes_in_reference(client: TestClient) -> None:
    """Permit reference WG7/2025/04001234 — slashes must survive routing."""
    work = _sample_work(permit="WG7/2025/04001234")
    mock = AsyncMock(return_value=work)
    with patch("routers.works.get_work_by_permit", mock):
        resp = client.get("/works/permit/WG7/2025/04001234")

    assert resp.status_code == 200
    mock.assert_called_once()
    _, called_permit = mock.call_args.args
    assert called_permit == "WG7/2025/04001234"


def test_get_permit_not_found_returns_404(client: TestClient) -> None:
    with patch("routers.works.get_work_by_permit", AsyncMock(return_value=None)):
        resp = client.get("/works/permit/XX1/2025/00000")

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ── GET /works/bbox ────────────────────────────────────────────────────────────

def test_get_by_bbox_returns_list(client: TestClient) -> None:
    works = [_sample_work("P1"), _sample_work("P2")]
    with patch("routers.works.get_works_by_bbox", AsyncMock(return_value=works)):
        resp = client.get("/works/bbox?min_lon=-2.0&min_lat=52.4&max_lon=-1.8&max_lat=52.6")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["permitReference"] == "P1"


def test_get_by_bbox_passes_params_to_repository(client: TestClient) -> None:
    mock = AsyncMock(return_value=[])
    with patch("routers.works.get_works_by_bbox", mock):
        client.get(
            "/works/bbox"
            "?min_lon=-2.0&min_lat=52.4&max_lon=-1.8&max_lat=52.6"
            "&status=granted&status=in_progress"
            "&from_date=2025-06-01&to_date=2025-06-30"
            "&limit=50"
        )

    mock.assert_called_once()
    _, kwargs = mock.call_args.args[0], mock.call_args.kwargs
    assert kwargs["bbox"] == (-2.0, 52.4, -1.8, 52.6)
    assert set(kwargs["statuses"]) == {"granted", "in_progress"}
    assert kwargs["from_date"] == date(2025, 6, 1)
    assert kwargs["to_date"] == date(2025, 6, 30)
    assert kwargs["limit"] == 50


def test_get_by_bbox_missing_required_param_returns_422(client: TestClient) -> None:
    resp = client.get("/works/bbox?min_lon=-2.0&min_lat=52.4&max_lon=-1.8")  # no max_lat
    assert resp.status_code == 422


def test_get_by_bbox_limit_enforced_by_validation(client: TestClient) -> None:
    """limit > 500 should be rejected by FastAPI query validation."""
    with patch("routers.works.get_works_by_bbox", AsyncMock(return_value=[])):
        resp = client.get(
            "/works/bbox?min_lon=-2.0&min_lat=52.4&max_lon=-1.8&max_lat=52.6&limit=9999"
        )
    assert resp.status_code == 422


def test_get_by_bbox_empty_result(client: TestClient) -> None:
    with patch("routers.works.get_works_by_bbox", AsyncMock(return_value=[])):
        resp = client.get("/works/bbox?min_lon=-2.0&min_lat=52.4&max_lon=-1.8&max_lat=52.6")

    assert resp.status_code == 200
    assert resp.json() == []


# ── GET /works/usrn/{usrn} ─────────────────────────────────────────────────────

def test_get_by_usrn_returns_works(client: TestClient) -> None:
    works = [_sample_work(usrn="41507223"), _sample_work("REF2", usrn="41507223")]
    with patch("routers.works.get_works_by_usrn", AsyncMock(return_value=works)):
        resp = client.get("/works/usrn/41507223")

    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_by_usrn_passes_status_filter(client: TestClient) -> None:
    mock = AsyncMock(return_value=[])
    with patch("routers.works.get_works_by_usrn", mock):
        client.get("/works/usrn/41507223?status=granted&status=in_progress")

    _, kwargs = mock.call_args.args[0], mock.call_args.kwargs
    assert set(kwargs["statuses"]) == {"granted", "in_progress"}


def test_get_by_usrn_empty_returns_empty_list(client: TestClient) -> None:
    with patch("routers.works.get_works_by_usrn", AsyncMock(return_value=[])):
        resp = client.get("/works/usrn/00000000")

    assert resp.status_code == 200
    assert resp.json() == []


# ── GET /works/authority/{authority} ──────────────────────────────────────────

def test_get_by_authority_returns_works(client: TestClient) -> None:
    works = [_sample_work(authority="Birmingham City Council")]
    with patch("routers.works.get_works_by_authority", AsyncMock(return_value=works)):
        resp = client.get("/works/authority/Birmingham City Council")

    assert resp.status_code == 200
    assert resp.json()[0]["authority"] == "Birmingham City Council"


def test_get_by_authority_passes_status_filter(client: TestClient) -> None:
    mock = AsyncMock(return_value=[])
    with patch("routers.works.get_works_by_authority", mock):
        client.get("/works/authority/Birmingham City Council?status=in_progress")

    _, kwargs = mock.call_args.args[0], mock.call_args.kwargs
    assert kwargs["statuses"] == ["in_progress"]


# ── camelCase across all list endpoints ───────────────────────────────────────

def test_list_response_uses_camel_case(client: TestClient) -> None:
    """All list endpoints must serialize to camelCase — spot-check bbox."""
    work = _sample_work()
    with patch("routers.works.get_works_by_bbox", AsyncMock(return_value=[work])):
        resp = client.get("/works/bbox?min_lon=-2.0&min_lat=52.4&max_lon=-1.8&max_lat=52.6")

    item = resp.json()[0]
    assert "permitReference" in item
    assert "streetName" in item
    assert "proposedStartDate" in item
    assert "permit_reference" not in item
