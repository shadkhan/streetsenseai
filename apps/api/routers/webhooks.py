"""Street Manager Open Data webhook receivers.

Street Manager POSTs event notifications to these endpoints when permit
lifecycle events occur. Each endpoint accepts the event payload, validates
it, and dispatches a Celery task to fetch the full permit details.

Three separate endpoint paths are required by the SM onboarding form:
  - /webhooks/permits    → permit lifecycle events (granted, started, etc.)
  - /webhooks/activities → activity / works update events
  - /webhooks/section58  → section 58 restriction events

All three share the same event payload shape (SMEventPayload) and the same
processing path: extract permit reference → dispatch process_sm_event task.

Delivery guarantee: SM expects a 2xx response within a few seconds or it
will retry. We return 202 immediately after queuing the Celery task —
never do slow work synchronously in these handlers.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, Response

from schemas.street_manager import SMEventPayload
from tasks.ingest import process_sm_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def _handle_sm_event(event_type: str, request: Request) -> dict[str, str]:
    """Parse the SM event payload, extract the permit reference, dispatch task."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    try:
        event = SMEventPayload.model_validate(body)
    except Exception as exc:
        logger.warning("SM %s webhook — payload validation failed: %s | body=%s", event_type, exc, body)
        # Return 200 rather than 4xx so SM doesn't retry a structurally bad payload
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
    process_sm_event.delay(event.object_reference)  # type: ignore[attr-defined]

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
