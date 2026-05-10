"""Tests for SM-005: Celery ingestion tasks.

Covers _do_rest_poll (the async core of poll_sm_rest) and poll_sm_sqs.
All external dependencies are mocked — no live Redis, DB, or SM API needed.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from schemas.domain import PointGeometry, StreetWork
from tasks.ingest import _FALLBACK_LOOKBACK_SECONDS, _POLL_LAST_RUN_KEY, _do_rest_poll


# ── Helpers ────────────────────────────────────────────────────────────────────

def _sample_work(permit: str = "WG7/2025/04001234") -> StreetWork:
    return StreetWork(
        permit_reference=permit,
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


def _make_redis(last_run_value: bytes | None = None) -> AsyncMock:
    r = AsyncMock()
    r.get = AsyncMock(return_value=last_run_value)
    r.set = AsyncMock()
    r.aclose = AsyncMock()
    return r


def _make_sm_client(works: list[StreetWork]) -> MagicMock:
    """Return a mock StreetManagerClient async context manager yielding works."""
    instance = AsyncMock()
    instance.get_works_since = AsyncMock(return_value=works)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=instance)
    cm.__aexit__ = AsyncMock(return_value=None)
    cls = MagicMock(return_value=cm)
    return cls


def _make_session_factory() -> tuple[MagicMock, AsyncMock]:
    """Return (factory, session) where factory() is an async context manager."""
    session = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=session_cm)
    return factory, session


# ── _do_rest_poll: cursor behaviour ───────────────────────────────────────────

async def test_first_run_defaults_to_15_minutes_ago() -> None:
    """No last-run key in Redis → since = now - 900s."""
    mock_redis = _make_redis(last_run_value=None)
    sm_cls = _make_sm_client([])
    factory, _ = _make_session_factory()

    fixed_now = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)

    with (
        patch("redis.asyncio.from_url", return_value=mock_redis),
        patch("services.street_manager.StreetManagerClient", sm_cls),
        patch("services.works_repository.upsert_work", AsyncMock()),
        patch("database.async_session_factory", factory),
        patch("tasks.ingest.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = fixed_now
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        result = await _do_rest_poll()

    expected_since = fixed_now - timedelta(seconds=_FALLBACK_LOOKBACK_SECONDS)
    assert result["since"] == expected_since.isoformat()
    assert result["upserted"] == 0


async def test_subsequent_run_uses_stored_cursor() -> None:
    """last-run key exists → since = stored timestamp."""
    stored_ts = datetime(2026, 5, 10, 11, 45, 0, tzinfo=timezone.utc)
    mock_redis = _make_redis(last_run_value=stored_ts.isoformat().encode())
    sm_cls = _make_sm_client([])
    factory, _ = _make_session_factory()

    with (
        patch("redis.asyncio.from_url", return_value=mock_redis),
        patch("services.street_manager.StreetManagerClient", sm_cls),
        patch("services.works_repository.upsert_work", AsyncMock()),
        patch("database.async_session_factory", factory),
    ):
        result = await _do_rest_poll()

    assert result["since"] == stored_ts.isoformat()


async def test_cursor_updated_to_now_after_run() -> None:
    """Redis.set must be called with the new 'now' timestamp after upserts."""
    fixed_now = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)
    mock_redis = _make_redis(last_run_value=None)
    sm_cls = _make_sm_client([])
    factory, _ = _make_session_factory()

    with (
        patch("redis.asyncio.from_url", return_value=mock_redis),
        patch("services.street_manager.StreetManagerClient", sm_cls),
        patch("services.works_repository.upsert_work", AsyncMock()),
        patch("database.async_session_factory", factory),
        patch("tasks.ingest.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = fixed_now
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        await _do_rest_poll()

    mock_redis.set.assert_called_once_with(_POLL_LAST_RUN_KEY, fixed_now.isoformat())


# ── _do_rest_poll: upsert behaviour ───────────────────────────────────────────

async def test_all_returned_works_are_upserted() -> None:
    works = [_sample_work("REF/2025/00001"), _sample_work("REF/2025/00002")]
    mock_redis = _make_redis(last_run_value=None)
    sm_cls = _make_sm_client(works)
    factory, _ = _make_session_factory()
    mock_upsert = AsyncMock()

    with (
        patch("redis.asyncio.from_url", return_value=mock_redis),
        patch("services.street_manager.StreetManagerClient", sm_cls),
        patch("services.works_repository.upsert_work", mock_upsert),
        patch("database.async_session_factory", factory),
    ):
        result = await _do_rest_poll()

    assert result["upserted"] == 2
    assert mock_upsert.call_count == 2


async def test_empty_results_upserts_nothing() -> None:
    mock_redis = _make_redis(last_run_value=None)
    sm_cls = _make_sm_client([])
    factory, _ = _make_session_factory()
    mock_upsert = AsyncMock()

    with (
        patch("redis.asyncio.from_url", return_value=mock_redis),
        patch("services.street_manager.StreetManagerClient", sm_cls),
        patch("services.works_repository.upsert_work", mock_upsert),
        patch("database.async_session_factory", factory),
    ):
        result = await _do_rest_poll()

    assert result["upserted"] == 0
    mock_upsert.assert_not_called()
    # Cursor must still be updated even with zero works
    mock_redis.set.assert_called_once()


async def test_redis_always_closed_on_success() -> None:
    mock_redis = _make_redis(last_run_value=None)
    sm_cls = _make_sm_client([])
    factory, _ = _make_session_factory()

    with (
        patch("redis.asyncio.from_url", return_value=mock_redis),
        patch("services.street_manager.StreetManagerClient", sm_cls),
        patch("services.works_repository.upsert_work", AsyncMock()),
        patch("database.async_session_factory", factory),
    ):
        await _do_rest_poll()

    mock_redis.aclose.assert_called_once()


async def test_redis_closed_even_when_sm_raises() -> None:
    """Redis connection must be released even if the SM API call fails."""
    mock_redis = _make_redis(last_run_value=None)

    failing_instance = AsyncMock()
    failing_instance.get_works_since = AsyncMock(side_effect=RuntimeError("SM API down"))
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=failing_instance)
    cm.__aexit__ = AsyncMock(return_value=None)
    sm_cls = MagicMock(return_value=cm)
    factory, _ = _make_session_factory()

    with (
        patch("redis.asyncio.from_url", return_value=mock_redis),
        patch("services.street_manager.StreetManagerClient", sm_cls),
        patch("services.works_repository.upsert_work", AsyncMock()),
        patch("database.async_session_factory", factory),
        pytest.raises(RuntimeError),
    ):
        await _do_rest_poll()

    mock_redis.aclose.assert_called_once()


# ── poll_sm_sqs ────────────────────────────────────────────────────────────────

def test_poll_sm_sqs_dispatches_per_permit() -> None:
    """Each valid SQS message produces one process_sm_event.delay() call."""
    from tasks.ingest import poll_sm_sqs

    mock_consumer = MagicMock()
    mock_consumer.poll.return_value = [
        {"ReceiptHandle": "rh-1"},
        {"ReceiptHandle": "rh-2"},
    ]
    # Both messages decode to valid notifications with permit references
    mock_consumer.decode_notification.return_value = MagicMock()
    mock_consumer.extract_permit_reference.side_effect = [
        "WG7/2025/00001",
        "WG7/2025/00002",
    ]

    with (
        patch("tasks.ingest.SQSConsumer", return_value=mock_consumer),
        patch("tasks.ingest.process_sm_event") as mock_task,
    ):
        mock_task.delay = MagicMock()
        result = poll_sm_sqs()  # bind=True: Celery injects self, don't pass it manually

    assert result == {"received": 2, "dispatched": 2}
    assert mock_task.delay.call_count == 2
    assert mock_consumer.delete_message.call_count == 2


def test_poll_sm_sqs_skips_malformed_messages() -> None:
    """Malformed messages (decode returns None) are deleted without dispatching."""
    from tasks.ingest import poll_sm_sqs

    mock_consumer = MagicMock()
    mock_consumer.poll.return_value = [{"ReceiptHandle": "bad"}]
    mock_consumer.decode_notification.return_value = None  # malformed

    with (
        patch("tasks.ingest.SQSConsumer", return_value=mock_consumer),
        patch("tasks.ingest.process_sm_event") as mock_task,
    ):
        mock_task.delay = MagicMock()
        result = poll_sm_sqs()

    assert result == {"received": 1, "dispatched": 0}
    mock_task.delay.assert_not_called()
    mock_consumer.delete_message.assert_called_once_with("bad")


def test_poll_sm_sqs_empty_queue_returns_zero() -> None:
    from tasks.ingest import poll_sm_sqs

    mock_consumer = MagicMock()
    mock_consumer.poll.return_value = []

    with patch("tasks.ingest.SQSConsumer", return_value=mock_consumer):
        result = poll_sm_sqs()

    assert result == {"received": 0, "dispatched": 0}
