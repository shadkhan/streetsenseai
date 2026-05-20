"""Tests for SM-001: Street Manager API client, JWT auth manager, and SQS consumer."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from schemas.domain import LineStringGeometry, PointGeometry
from services.street_manager import StreetManagerAuthManager, StreetManagerClient, normalize_permit


# ── normalize_permit ───────────────────────────────────────────────────────────

def _permit_raw(overrides: dict | None = None) -> dict:
    base = {
        "permit_reference_number": "WG7/2025/04001234",
        "works_reference_number": "WG7/2025/04001234",
        "usrn": "41507223",
        "street_name": "Corporation Street",
        "area_name": "Birmingham City Council",
        "promoter_organisation": "Cadent Gas",
        "promoter_swa_code": "WG7",
        "work_category": "Standard",
        "traffic_management_type": "Two-way signals",
        "restriction_type": "Lane closure",
        "proposed_start_date": "2025-06-01",
        "proposed_end_date": "2025-06-07",
        "permit_status": "granted",
        "geometry": {"type": "Point", "coordinates": [-1.8979, 52.4862]},
    }
    if overrides:
        base.update(overrides)
    return base


def test_normalize_permit_point_geometry() -> None:
    work = normalize_permit(_permit_raw())

    assert work is not None
    assert work.permit_reference == "WG7/2025/04001234"
    assert work.usrn == "41507223"
    assert work.street_name == "Corporation Street"
    assert work.authority == "Birmingham City Council"
    assert work.promoter == "Cadent Gas"
    assert work.promoter_licence_number == "WG7"
    assert work.status == "granted"
    assert isinstance(work.geometry, PointGeometry)
    assert work.geometry.coordinates == (-1.8979, 52.4862)


def test_normalize_permit_linestring_geometry() -> None:
    raw = _permit_raw({
        "permit_reference_number": "AB123/2025/00001",
        "permit_status": "in_progress",
        "geometry": {
            "type": "LineString",
            "coordinates": [[-1.5, 53.8], [-1.51, 53.81], [-1.52, 53.82]],
        },
    })
    work = normalize_permit(raw)

    assert work is not None
    assert work.status == "in_progress"
    assert isinstance(work.geometry, LineStringGeometry)
    assert len(work.geometry.coordinates) == 3
    assert work.geometry.coordinates[0] == (-1.5, 53.8)


def test_normalize_permit_missing_geometry_returns_none() -> None:
    assert normalize_permit(_permit_raw({"geometry": None})) is None


def test_normalize_permit_unsupported_geometry_returns_none() -> None:
    raw = _permit_raw({"geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1]]]}})
    assert normalize_permit(raw) is None


def test_normalize_permit_unknown_status_defaults_to_submitted() -> None:
    work = normalize_permit(_permit_raw({"permit_status": "some_future_api_status"}))
    assert work is not None
    assert work.status == "submitted"


def test_normalize_permit_all_known_statuses() -> None:
    known = [
        "submitted", "granted", "permit_modification_request",
        "refused", "revoked", "in_progress", "completed", "closed",
    ]
    for status in known:
        work = normalize_permit(_permit_raw({"permit_status": status}))
        assert work is not None, f"Expected work for status={status}"
        assert work.status == status


def test_normalize_permit_malformed_returns_none() -> None:
    # Missing permit_reference_number — validation should fail gracefully
    assert normalize_permit({"usrn": "12345"}) is None


def test_normalize_permit_camelcase_json() -> None:
    work = normalize_permit(_permit_raw())
    assert work is not None
    dumped = work.model_dump(by_alias=True)
    assert "permitReference" in dumped
    assert "streetName" in dumped
    assert "promoterLicenceNumber" in dumped


# ── Shared fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def mock_redis() -> MagicMock:
    r = MagicMock()
    r.get = AsyncMock(return_value=None)
    r.setex = AsyncMock(return_value=True)
    r.delete = AsyncMock(return_value=True)
    return r


def _make_auth_http(id_token: str = "id-tok-abc", refresh_token: str = "ref-tok-xyz") -> MagicMock:
    """Return a mock httpx.AsyncClient whose POST returns a valid SM auth response."""
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json = MagicMock(return_value={
        "id_token": id_token,
        "access_token": "access-tok",
        "refresh_token": refresh_token,
    })
    mock_resp.raise_for_status = MagicMock()

    mock_http = MagicMock(spec=httpx.AsyncClient)
    mock_http.post = AsyncMock(return_value=mock_resp)
    return mock_http


# ── StreetManagerAuthManager tests ────────────────────────────────────────────

async def test_auth_manager_gets_token_on_first_call(mock_redis: MagicMock) -> None:
    """On first call (no cached token), should authenticate and cache the id_token."""
    auth_http = _make_auth_http(id_token="fresh-token")
    manager = StreetManagerAuthManager(redis=mock_redis, http=auth_http)

    token = await manager.get_token()

    assert token == "fresh-token"
    # Should have called /v3/party/authenticate
    auth_http.post.assert_called_once()
    call_url: str = auth_http.post.call_args[0][0]
    assert "/v3/party/authenticate" in call_url
    # Should have cached the token with 55-minute TTL
    mock_redis.setex.assert_called()
    ttl_arg = mock_redis.setex.call_args_list[0][0][1]
    assert ttl_arg == StreetManagerAuthManager._TOKEN_TTL


async def test_auth_manager_uses_cached_token(mock_redis: MagicMock) -> None:
    """When Redis has a cached id_token, no HTTP call should be made."""
    mock_redis.get = AsyncMock(return_value=b"cached-token")
    auth_http = _make_auth_http()
    manager = StreetManagerAuthManager(redis=mock_redis, http=auth_http)

    token = await manager.get_token()

    assert token == "cached-token"
    auth_http.post.assert_not_called()


async def test_auth_manager_refreshes_on_expiry(mock_redis: MagicMock) -> None:
    """When id_token is absent but refresh_token is cached, use /v3/party/refresh."""
    # First get returns None (id_token expired), second returns a refresh token
    mock_redis.get = AsyncMock(side_effect=[None, b"stored-refresh-tok"])

    refreshed_resp = MagicMock(spec=httpx.Response)
    refreshed_resp.status_code = 200
    refreshed_resp.json = MagicMock(return_value={
        "id_token": "refreshed-id-token",
        "refresh_token": "new-refresh-tok",
    })
    refreshed_resp.raise_for_status = MagicMock()

    auth_http = MagicMock(spec=httpx.AsyncClient)
    auth_http.post = AsyncMock(return_value=refreshed_resp)
    manager = StreetManagerAuthManager(redis=mock_redis, http=auth_http)

    token = await manager.get_token()

    assert token == "refreshed-id-token"
    call_url: str = auth_http.post.call_args[0][0]
    assert "/v3/party/refresh" in call_url
    body = auth_http.post.call_args[1]["json"]
    assert body["refresh_token"] == "stored-refresh-tok"


async def test_auth_manager_retries_on_401(mock_redis: MagicMock) -> None:
    """StreetManagerClient should invalidate the cached token and retry once on 401."""
    # Auth manager always returns a fresh token
    auth_manager = MagicMock(spec=StreetManagerAuthManager)
    auth_manager.get_token = AsyncMock(return_value="new-token-after-401")
    auth_manager.invalidate = AsyncMock()

    # First HTTP GET returns 401, second returns 200
    resp_401 = MagicMock(spec=httpx.Response)
    resp_401.status_code = 401

    resp_200 = MagicMock(spec=httpx.Response)
    resp_200.status_code = 200
    resp_200.json = MagicMock(return_value={"works": [], "pagination_cursor": None})
    resp_200.raise_for_status = MagicMock()

    mock_http = MagicMock(spec=httpx.AsyncClient)
    mock_http.get = AsyncMock(side_effect=[resp_401, resp_200])
    mock_http.aclose = AsyncMock()

    client = StreetManagerClient(
        mock_redis, http_client=mock_http, auth_manager=auth_manager
    )

    # Patch _get's tenacity decorator away to test 401 logic directly
    result = await client._get.__wrapped__(client, "/works")

    assert result == {"works": [], "pagination_cursor": None}
    auth_manager.invalidate.assert_called_once()
    assert mock_http.get.call_count == 2


# ── StreetManagerClient ────────────────────────────────────────────────────────

@pytest.fixture
def sm_client(mock_redis: MagicMock) -> StreetManagerClient:
    # Inject mock HTTP and a pre-configured auth manager so tests never make real SSL calls
    mock_http = MagicMock(spec=httpx.AsyncClient)
    mock_http.aclose = AsyncMock()
    mock_auth = MagicMock(spec=StreetManagerAuthManager)
    mock_auth.get_token = AsyncMock(return_value="test-id-token")
    mock_auth.invalidate = AsyncMock()
    return StreetManagerClient(mock_redis, http_client=mock_http, auth_manager=mock_auth)


async def test_get_work_cache_miss_calls_api(
    sm_client: StreetManagerClient, mock_redis: MagicMock
) -> None:
    with patch.object(sm_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _permit_raw()

        work = await sm_client.get_work("WG7/2025/04001234")

        mock_get.assert_called_once()
        assert work is not None
        assert work.permit_reference == "WG7/2025/04001234"
        assert work.status == "granted"
        mock_redis.setex.assert_called_once()


async def test_get_work_cache_hit_skips_api(
    sm_client: StreetManagerClient, mock_redis: MagicMock
) -> None:
    mock_redis.get = AsyncMock(return_value=json.dumps(_permit_raw()).encode())

    with patch.object(sm_client, "_get", new_callable=AsyncMock) as mock_get:
        work = await sm_client.get_work("WG7/2025/04001234")

        mock_get.assert_not_called()
        assert work is not None
        assert work.permit_reference == "WG7/2025/04001234"


async def test_get_work_404_returns_none(
    sm_client: StreetManagerClient, mock_redis: MagicMock
) -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    http_error = httpx.HTTPStatusError(
        "Not Found", request=MagicMock(), response=mock_response
    )

    with patch.object(sm_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = http_error
        work = await sm_client.get_work("WG7/2025/NOTEXIST")
        assert work is None


async def test_get_works_by_bbox_returns_normalized_list(
    sm_client: StreetManagerClient, mock_redis: MagicMock
) -> None:
    api_response = {
        "works": [_permit_raw(), _permit_raw({"permit_reference_number": "WG7/2025/00002"})],
        "pagination_cursor": None,
    }

    with patch.object(sm_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = api_response

        works, cursor = await sm_client.get_works_by_bbox(
            bbox=(-2.0, 52.0, -1.5, 52.5)
        )

        assert len(works) == 2
        assert cursor is None
        call_params = mock_get.call_args
        assert "/works" in call_params[0][0]


async def test_get_works_by_bbox_uses_cursor(
    sm_client: StreetManagerClient, mock_redis: MagicMock
) -> None:
    api_response = {
        "works": [_permit_raw()],
        "pagination_cursor": "next-page-token",
    }

    with patch.object(sm_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = api_response

        works, cursor = await sm_client.get_works_by_bbox(
            bbox=(-2.0, 52.0, -1.5, 52.5), cursor="page-1"
        )

        assert cursor == "next-page-token"
        _, kwargs = mock_get.call_args
        assert kwargs.get("params", {}).get("pagination_cursor") == "page-1"


# ── SQSConsumer ────────────────────────────────────────────────────────────────

def _make_sqs_message(event_type: str = "WORK_START", permit_ref: str = "WG7/2025/04001234") -> dict:
    event_payload = {
        "event_reference": 123456,
        "event_type": event_type,
        "object_type": "PERMIT",
        "object_reference": permit_ref,
        "event_time": "2025-06-01T10:00:00Z",
    }
    envelope = {
        "Type": "Notification",
        "MessageId": "abc-123",
        "TopicArn": "arn:aws:sns:eu-west-2:123456789012:street-manager-events",
        "Message": json.dumps(event_payload),
        "Timestamp": "2025-06-01T10:00:00.000Z",
    }
    return {
        "Body": json.dumps(envelope),
        "ReceiptHandle": "receipt-handle-abc",
        "MessageId": "abc-123",
    }


def test_decode_notification_valid() -> None:
    from services.sqs_consumer import SQSConsumer

    consumer = SQSConsumer(sqs_client=MagicMock())
    notification = consumer.decode_notification(_make_sqs_message())

    assert notification is not None
    assert notification.Type == "Notification"
    assert notification.MessageId == "abc-123"


def test_decode_notification_malformed_returns_none() -> None:
    from services.sqs_consumer import SQSConsumer

    consumer = SQSConsumer(sqs_client=MagicMock())
    assert consumer.decode_notification({"Body": "not json", "ReceiptHandle": "r"}) is None


def test_extract_permit_reference_valid() -> None:
    from services.sqs_consumer import SQSConsumer

    consumer = SQSConsumer(sqs_client=MagicMock())
    notification = consumer.decode_notification(_make_sqs_message(permit_ref="WG7/2025/04001234"))
    assert notification is not None

    ref = consumer.extract_permit_reference(notification)
    assert ref == "WG7/2025/04001234"


def test_extract_permit_reference_subscription_confirmation_returns_none() -> None:
    from services.sqs_consumer import SQSConsumer

    consumer = SQSConsumer(sqs_client=MagicMock())
    confirm_envelope = {
        "Type": "SubscriptionConfirmation",
        "MessageId": "sub-confirm-1",
        "TopicArn": "arn:aws:sns:eu-west-2:123456789012:street-manager-events",
        "Message": "You have chosen to subscribe to the topic.",
        "Timestamp": "2025-06-01T09:00:00.000Z",
        "SubscribeURL": "https://sns.amazonaws.com/confirm?token=abc",
    }
    sqs_msg = {"Body": json.dumps(confirm_envelope), "ReceiptHandle": "r-sub"}
    notification = consumer.decode_notification(sqs_msg)
    assert notification is not None
    assert consumer.extract_permit_reference(notification) is None


def test_poll_no_queue_url_returns_empty() -> None:
    from services.sqs_consumer import SQSConsumer
    from unittest.mock import patch

    with patch("services.sqs_consumer.settings") as mock_settings:
        mock_settings.street_manager_sqs_queue_url = ""
        consumer = SQSConsumer(sqs_client=MagicMock())
        assert consumer.poll() == []
