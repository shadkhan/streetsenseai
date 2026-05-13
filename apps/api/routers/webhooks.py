"""Street Manager Open Data webhook receivers.

Street Manager POSTs event notifications to these endpoints (via AWS SNS) when
permit lifecycle events occur. Each endpoint validates the payload and dispatches
a Celery task to fetch the full permit details.

Three separate endpoint paths are required by the SM onboarding form:
  - /webhooks/permits    → permit lifecycle events (granted, started, etc.)
  - /webhooks/activities → activity / works update events
  - /webhooks/section58  → section 58 restriction events

All three share the same processing path:
  1. Detect and handle AWS SNS envelope (SubscriptionConfirmation or Notification)
  2. For Notification: extract inner SMEventPayload from the Message field
  3. Dispatch process_sm_event Celery task with the permit reference

Delivery guarantee: SM/SNS expects a 2xx response within a few seconds or it
will retry. We return 202 immediately after queuing the task — never block here.
"""
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException, Request

from schemas.street_manager import SMEventPayload, SNSNotificationEnvelope
from tasks.ingest import process_sm_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def _confirm_sns_subscription(url: str) -> None:
    """Visit the SNS SubscribeURL to confirm the subscription."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.get(url)


async def _handle_sm_event(event_type: str, request: Request) -> dict[str, str]:
    """Detect SNS envelope or direct payload, extract permit reference, dispatch task."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event: SMEventPayload | None = None

    # SNS envelopes always contain "Type" and "TopicArn" — use these as the discriminator
    if isinstance(body, dict) and "Type" in body and "TopicArn" in body:
        try:
            envelope = SNSNotificationEnvelope.model_validate(body)
        except Exception as exc:
            logger.warning("SM %s webhook — SNS envelope validation failed: %s", event_type, exc)
            return {"status": "ignored", "reason": "invalid_sns_envelope"}

        if envelope.Type == "SubscriptionConfirmation":
            if envelope.SubscribeURL:
                try:
                    await _confirm_sns_subscription(str(envelope.SubscribeURL))
                    logger.info("SM %s webhook — SNS subscription confirmed", event_type)
                except Exception as exc:
                    logger.error("SM %s webhook — subscription confirm failed: %s", event_type, exc)
            return {"status": "subscription_confirmed"}

        if envelope.Type == "UnsubscribeConfirmation":
            logger.info("SM %s webhook — SNS unsubscribe confirmation received", event_type)
            return {"status": "ignored", "reason": "unsubscribe_confirmation"}

        # Notification — inner SM event is a JSON string in Message
        try:
            event = envelope.parse_message()
        except Exception as exc:
            logger.warning("SM %s webhook — SNS message parse failed: %s", event_type, exc)
            return {"status": "ignored", "reason": "invalid_message"}
    else:
        # Direct payload (non-SNS path, e.g. manual testing or future SM changes)
        try:
            event = SMEventPayload.model_validate(body)
        except Exception as exc:
            logger.warning("SM %s webhook — payload validation failed: %s | body=%s", event_type, exc, body)
            return {"status": "ignored", "reason": "validation_failed"}

    if not event.object_reference:
        logger.debug("SM %s webhook — no object_reference in event %s", event_type, event.event_reference)
        return {"status": "ignored", "reason": "no_object_reference"}

    logger.info(
        "SM %s webhook — event=%s type=%s permit=%s",
        event_type,
        event.event_reference,
        event.event_type,
        event.object_reference,
    )

    # Dispatch to Celery worker — returns immediately, worker fetches full permit
    process_sm_event.delay(event.object_reference)
    return {"status": "accepted", "permit_reference": event.object_reference}


@router.post("/permits", status_code=202)
async def receive_permit_event(request: Request) -> dict[str, str]:
    """Receive Street Manager permit lifecycle event notifications.

    Triggered by: PERMIT_SUBMITTED, PERMIT_GRANTED, PERMIT_REFUSED,
    PERMIT_REVOKED, WORK_START, WORK_STOP, PERMIT_CLOSED, etc.
    """
    return await _handle_sm_event("permits", request)


@router.post("/activities", status_code=202)
async def receive_activity_event(request: Request) -> dict[str, str]:
    """Receive Street Manager activity / works update notifications.

    Triggered by: ACTIVITY_CREATED, ACTIVITY_UPDATED, ACTIVITY_CANCELLED.
    """
    return await _handle_sm_event("activities", request)


@router.post("/section58", status_code=202)
async def receive_section58_event(request: Request) -> dict[str, str]:
    """Receive Street Manager section 58 restriction notifications.

    Triggered by: SECTION_58_CREATED, SECTION_58_MODIFIED, SECTION_58_EXPIRED.
    """
    return await _handle_sm_event("section58", request)
