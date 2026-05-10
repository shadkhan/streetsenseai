"""Celery ingestion tasks for Street Manager data.

SM-001 — SQS consumer task (poll_sm_sqs):
  Runs every 30 seconds via Celery Beat. Polls the Street Manager SQS queue
  for new permit events. Dispatches process_sm_event for each event received.

SM-005 — Polling fallback task (poll_sm_rest):
  Runs every 15 minutes. Calls the Street Manager REST API for any works
  updated since the last run. Acts as a safety net when SQS events are missed.
  Tracks the last-run cursor in Redis under key sm_rest_last_poll.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from celery_app import celery
from services.sqs_consumer import SQSConsumer

logger = logging.getLogger(__name__)

# ── SM-005 constants ───────────────────────────────────────────────────────────

_POLL_LAST_RUN_KEY = "sm_rest_last_poll"
_FALLBACK_LOOKBACK_SECONDS = 900  # 15 min — matches the Beat schedule interval


@celery.task(name="tasks.ingest.poll_sm_sqs", bind=True, max_retries=3)  # type: ignore[misc]
def poll_sm_sqs(self: Any) -> dict[str, int]:  # type: ignore[misc]
    """SM-001: Poll the Street Manager SQS queue for new work events.

    Scheduled every 30 seconds by Celery Beat (see celery_app.py).
    Dispatches one process_sm_event task per permit reference received.
    """
    consumer = SQSConsumer()
    messages = consumer.poll()

    dispatched = 0
    for message in messages:
        receipt_handle: str = message.get("ReceiptHandle", "")

        notification = consumer.decode_notification(message)
        if notification is None:
            # Malformed message — delete to avoid redelivery loop
            consumer.delete_message(receipt_handle)
            continue

        permit_reference = consumer.extract_permit_reference(notification)
        if permit_reference:
            process_sm_event.delay(permit_reference)  # type: ignore[attr-defined]
            dispatched += 1

        consumer.delete_message(receipt_handle)

    logger.info("SM SQS poll complete: %d received, %d dispatched", len(messages), dispatched)
    return {"received": len(messages), "dispatched": dispatched}


@celery.task(name="tasks.ingest.process_sm_event", bind=True, max_retries=3)  # type: ignore[misc]
def process_sm_event(self: Any, permit_reference: str) -> dict[str, str]:  # type: ignore[misc]
    """SM-001 + SM-002: Fetch a Street Manager permit and persist it to the DB.

    Called by:
      - poll_sm_sqs (SM-001 SQS path)
      - webhooks router (SM-001 webhook path)
      - poll_sm_rest (SM-005 polling fallback)

    Flow: SM REST API -> StreetManagerClient -> StreetWork domain model
          -> works_repository.upsert_work -> PostgreSQL + PostGIS
    """

    async def _run() -> dict[str, str]:
        import redis.asyncio as aioredis

        from config import settings
        from database import async_session_factory
        from services.street_manager import StreetManagerClient
        from services.works_repository import upsert_work

        r: aioredis.Redis = aioredis.from_url(settings.redis_url)
        async with StreetManagerClient(r) as client:
            try:
                work = await client.get_work(permit_reference)
            finally:
                await r.aclose()

        if work is None:
            logger.warning("SM permit %s not found or has no geometry", permit_reference)
            return {"status": "not_found", "permit_reference": permit_reference}

        async with async_session_factory() as session:
            await upsert_work(session, work)

        logger.info(
            "Persisted SM permit %s -- %s (%s, %s)",
            work.permit_reference,
            work.street_name,
            work.authority,
            work.status,
        )
        return {"status": "ok", "permit_reference": permit_reference}

    return asyncio.run(_run())


# ── SM-005: REST polling fallback ──────────────────────────────────────────────

async def _do_rest_poll() -> dict[str, Any]:
    """Async core of poll_sm_rest — module-level so tests can await it directly.

    Reads the last-run cursor from Redis, fetches all works updated since that
    time, upserts each one, then advances the cursor to now.
    """
    import redis.asyncio as aioredis

    from config import settings
    from database import async_session_factory
    from services.street_manager import StreetManagerClient
    from services.works_repository import upsert_work

    now = datetime.now(timezone.utc)
    r: aioredis.Redis = aioredis.from_url(settings.redis_url)
    upserted = 0
    since: datetime

    try:
        last_run_raw = await r.get(_POLL_LAST_RUN_KEY)
        since = (
            datetime.fromisoformat(last_run_raw.decode())
            if last_run_raw
            else now - timedelta(seconds=_FALLBACK_LOOKBACK_SECONDS)
        )

        async with StreetManagerClient(r) as client:
            works = await client.get_works_since(since)

        if works:
            async with async_session_factory() as session:
                for work in works:
                    await upsert_work(session, work)
                    upserted += 1

        await r.set(_POLL_LAST_RUN_KEY, now.isoformat())
    finally:
        await r.aclose()

    logger.info(
        "SM REST poll complete: %d works upserted since %s",
        upserted,
        since.isoformat(),
    )
    return {"upserted": upserted, "since": since.isoformat()}


@celery.task(name="tasks.ingest.poll_sm_rest", bind=True, max_retries=3)  # type: ignore[misc]
def poll_sm_rest(self: Any) -> dict[str, Any]:  # type: ignore[misc]
    """SM-005: Poll the Street Manager REST API for works updated since last run.

    Scheduled every 15 minutes by Celery Beat (see celery_app.py).
    Acts as a safety net for permits missed by the webhook or SQS paths.
    Cursor is stored in Redis under key 'sm_rest_last_poll'.
    """
    return asyncio.run(_do_rest_poll())
