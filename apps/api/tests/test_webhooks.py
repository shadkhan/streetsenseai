"""Tests for Street Manager webhook endpoints (SM-001 webhook path).

Covers all three endpoints (/webhooks/permits, /webhooks/activities,
/webhooks/section58) via parametrize.  External dependencies — Celery task
and the SNS SubscribeURL fetch — are mocked throughout.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app

_client = TestClient(app)

_ENDPOINTS = ["/webhooks/permits", "/webhooks/activities", "/webhooks/section58"]
_PERMIT_REF = "WG7/2026/01234567"


# ── Payload builders ───────────────────────────────────────────────────────────

def _sns_notification(permit_ref: str = _PERMIT_REF) -> dict:
    """SNS Notification envelope wrapping a valid SMEventPayload."""
    inner = {
        "event_reference": 99001,
        "event_type": "PERMIT_GRANTED",
        "object_type": "PERMIT",
        "object_reference": permit_ref,
        "event_time": "2026-05-13T12:00:00+00:00",
    }
    return {
        "Type": "Notification",
        "MessageId": "msg-001",
        "TopicArn": "arn:aws:sns:eu-west-2:123456789012:street-manager-topic",
        "Message": json.dumps(inner),
        "Timestamp": "2026-05-13T12:00:00.000Z",
        "Signature": "dummysig",
    }


def _sns_subscription_confirmation(
    subscribe_url: str = "https://sns.eu-west-2.amazonaws.com/?Action=ConfirmSubscription&Token=abc",
) -> dict:
    return {
        "Type": "SubscriptionConfirmation",
        "MessageId": "msg-sub-001",
        "TopicArn": "arn:aws:sns:eu-west-2:123456789012:street-manager-topic",
        "Message": "You have chosen to subscribe to the topic.",
        "Timestamp": "2026-05-13T12:00:00.000Z",
        "SubscribeURL": subscribe_url,
        "Signature": "dummysig",
    }


def _direct_payload(permit_ref: str = _PERMIT_REF) -> dict:
    """Direct SMEventPayload (no SNS envelope) for manual / testing delivery."""
    return {
        "event_reference": 99001,
        "event_type": "PERMIT_GRANTED",
        "object_type": "PERMIT",
        "object_reference": permit_ref,
        "event_time": "2026-05-13T12:00:00+00:00",
    }


# ── SNS Notification ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", _ENDPOINTS)
def test_sns_notification_accepted(path: str) -> None:
    """SNS Notification on all three endpoints → 202 accepted."""
    with patch("routers.webhooks.process_sm_event") as mock_task:
        mock_task.delay = MagicMock()
        resp = _client.post(path, json=_sns_notification())
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["permit_reference"] == _PERMIT_REF
    mock_task.delay.assert_called_once_with(_PERMIT_REF)


@pytest.mark.parametrize("path", _ENDPOINTS)
def test_sns_notification_custom_permit(path: str) -> None:
    """Correct permit reference is extracted and dispatched."""
    ref = "AB12/2026/00099999"
    with patch("routers.webhooks.process_sm_event") as mock_task:
        mock_task.delay = MagicMock()
        _client.post(path, json=_sns_notification(ref))
    mock_task.delay.assert_called_once_with(ref)


@pytest.mark.parametrize("path", _ENDPOINTS)
def test_sns_notification_no_object_reference_ignored(path: str) -> None:
    """SNS Notification with no object_reference → 202 ignored, task not dispatched."""
    payload = _sns_notification()
    inner = json.loads(payload["Message"])
    del inner["object_reference"]
    payload["Message"] = json.dumps(inner)
    with patch("routers.webhooks.process_sm_event") as mock_task:
        mock_task.delay = MagicMock()
        resp = _client.post(path, json=payload)
    assert resp.status_code == 202
    assert resp.json() == {"status": "ignored", "reason": "no_object_reference"}
    mock_task.delay.assert_not_called()


@pytest.mark.parametrize("path", _ENDPOINTS)
def test_sns_notification_null_object_reference_ignored(path: str) -> None:
    """SNS Notification with object_reference=null → 202 ignored."""
    payload = _sns_notification()
    inner = json.loads(payload["Message"])
    inner["object_reference"] = None
    payload["Message"] = json.dumps(inner)
    with patch("routers.webhooks.process_sm_event") as mock_task:
        mock_task.delay = MagicMock()
        resp = _client.post(path, json=payload)
    assert resp.status_code == 202
    assert resp.json()["status"] == "ignored"


# ── SNS SubscriptionConfirmation ──────────────────────────────────────────────

@pytest.mark.parametrize("path", _ENDPOINTS)
def test_subscription_confirmation_confirmed(path: str) -> None:
    """SNS SubscriptionConfirmation → 202 subscription_confirmed, SubscribeURL visited."""
    subscribe_url = "https://sns.eu-west-2.amazonaws.com/?Action=ConfirmSubscription&Token=abc"
    with patch("routers.webhooks._confirm_sns_subscription", new_callable=AsyncMock) as mock_confirm:
        resp = _client.post(path, json=_sns_subscription_confirmation(subscribe_url))
    assert resp.status_code == 202
    assert resp.json() == {"status": "subscription_confirmed"}
    mock_confirm.assert_called_once_with(subscribe_url)


@pytest.mark.parametrize("path", _ENDPOINTS)
def test_subscription_confirmation_no_subscribe_url(path: str) -> None:
    """SubscriptionConfirmation with no SubscribeURL still returns subscription_confirmed."""
    payload = _sns_subscription_confirmation()
    del payload["SubscribeURL"]
    with patch("routers.webhooks._confirm_sns_subscription", new_callable=AsyncMock) as mock_confirm:
        resp = _client.post(path, json=payload)
    assert resp.status_code == 202
    assert resp.json()["status"] == "subscription_confirmed"
    mock_confirm.assert_not_called()


# ── Direct payload (non-SNS) ──────────────────────────────────────────────────

@pytest.mark.parametrize("path", _ENDPOINTS)
def test_direct_payload_accepted(path: str) -> None:
    """Direct SMEventPayload (no SNS wrapper) → 202 accepted."""
    with patch("routers.webhooks.process_sm_event") as mock_task:
        mock_task.delay = MagicMock()
        resp = _client.post(path, json=_direct_payload())
    assert resp.status_code == 202
    assert resp.json()["status"] == "accepted"
    mock_task.delay.assert_called_once_with(_PERMIT_REF)


# ── Error handling ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", _ENDPOINTS)
def test_invalid_json_returns_400(path: str) -> None:
    """Malformed JSON body → 400."""
    resp = _client.post(path, content=b"not-json", headers={"Content-Type": "application/json"})
    assert resp.status_code == 400


@pytest.mark.parametrize("path", _ENDPOINTS)
def test_garbage_body_ignored(path: str) -> None:
    """Valid JSON with unrecognised shape → 202 ignored, no task dispatched."""
    with patch("routers.webhooks.process_sm_event") as mock_task:
        mock_task.delay = MagicMock()
        resp = _client.post(path, json={"garbage": "data"})
    assert resp.status_code == 202
    assert resp.json()["status"] == "ignored"
    mock_task.delay.assert_not_called()


@pytest.mark.parametrize("path", _ENDPOINTS)
def test_invalid_sns_notification_message_ignored(path: str) -> None:
    """SNS Notification whose Message field is not valid JSON → 202 ignored."""
    payload = _sns_notification()
    payload["Message"] = "this is not json"
    with patch("routers.webhooks.process_sm_event") as mock_task:
        mock_task.delay = MagicMock()
        resp = _client.post(path, json=payload)
    assert resp.status_code == 202
    assert resp.json()["status"] == "ignored"
    mock_task.delay.assert_not_called()
