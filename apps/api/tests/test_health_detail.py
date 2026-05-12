"""Tests for SM-007: /health/detail endpoint."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from database import get_db, get_redis
from main import app

client = TestClient(app)

_NOW = datetime.now(timezone.utc)
_RECENT_TS = (_NOW - timedelta(minutes=5)).isoformat()
_STALE_TS = (_NOW - timedelta(minutes=25)).isoformat()

_DB_OK: dict[str, object] = {
    "status": "ok",
    "total_works": 5045,
    "most_recent_permit": {"reference": "WG7/2026/00001", "timestamp": _RECENT_TS},
    "postgis_version": "3.5 USE_GEOS=1 USE_PROJ=1",
}

_CACHE_OK: dict[str, object] = {
    "status": "ok",
    "redis_memory_used": "1.50M",
    "usrn_cache_hits": 42,
}

_INGESTION_OK: dict[str, object] = {
    "last_webhook_received": _RECENT_TS,
    "last_poll_run": _RECENT_TS,
    "works_ingested_24h": 150,
    "works_ingested_1h": 12,
}

_INGESTION_STALE: dict[str, object] = {
    "last_webhook_received": _STALE_TS,
    "last_poll_run": _STALE_TS,
    "works_ingested_24h": 0,
    "works_ingested_1h": 0,
}


@pytest.fixture(autouse=True)
def override_db_and_redis() -> None:
    """Prevent real DB / Redis connections for all tests in this module."""
    mock_session = AsyncMock()
    mock_redis = AsyncMock()

    async def _mock_get_db():  # type: ignore[return]
        yield mock_session

    async def _mock_get_redis():  # type: ignore[return]
        yield mock_redis

    app.dependency_overrides[get_db] = _mock_get_db
    app.dependency_overrides[get_redis] = _mock_get_redis
    yield  # type: ignore[misc]
    app.dependency_overrides.clear()


def test_health_detail_ok() -> None:
    """All systems healthy -> status is 'ok'."""
    with (
        patch("routers.health._db_health", AsyncMock(return_value=_DB_OK)),
        patch("routers.health._cache_health", AsyncMock(return_value=_CACHE_OK)),
        patch("routers.health._ingestion_health", AsyncMock(return_value=_INGESTION_OK)),
    ):
        resp = client.get("/health/detail")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_detail_degraded_redis() -> None:
    """Redis unreachable -> status is 'degraded'."""
    with (
        patch("routers.health._db_health", AsyncMock(return_value=_DB_OK)),
        patch(
            "routers.health._cache_health",
            AsyncMock(side_effect=ConnectionError("Redis down")),
        ),
        patch("routers.health._ingestion_health", AsyncMock(return_value=_INGESTION_OK)),
    ):
        resp = client.get("/health/detail")

    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded"


def test_health_detail_degraded_stale() -> None:
    """Last webhook older than 20 minutes -> status is 'degraded'."""
    with (
        patch("routers.health._db_health", AsyncMock(return_value=_DB_OK)),
        patch("routers.health._cache_health", AsyncMock(return_value=_CACHE_OK)),
        patch("routers.health._ingestion_health", AsyncMock(return_value=_INGESTION_STALE)),
    ):
        resp = client.get("/health/detail")

    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded"


def test_health_detail_db_error() -> None:
    """Database unreachable -> status is 'error'."""
    with (
        patch(
            "routers.health._db_health",
            AsyncMock(side_effect=Exception("DB connection refused")),
        ),
        patch("routers.health._cache_health", AsyncMock(return_value=_CACHE_OK)),
        patch("routers.health._ingestion_health", AsyncMock(return_value=_INGESTION_OK)),
    ):
        resp = client.get("/health/detail")

    assert resp.status_code == 200
    assert resp.json()["status"] == "error"


def test_health_detail_structure() -> None:
    """Response must contain all required top-level and nested keys."""
    with (
        patch("routers.health._db_health", AsyncMock(return_value=_DB_OK)),
        patch("routers.health._cache_health", AsyncMock(return_value=_CACHE_OK)),
        patch("routers.health._ingestion_health", AsyncMock(return_value=_INGESTION_OK)),
    ):
        resp = client.get("/health/detail")

    assert resp.status_code == 200
    body = resp.json()

    for key in ("status", "timestamp", "database", "ingestion", "cache", "phase", "system"):
        assert key in body, f"Missing top-level key: {key}"

    for key in ("status", "total_works", "most_recent_permit", "postgis_version"):
        assert key in body["database"], f"Missing database key: {key}"

    for key in ("last_webhook_received", "last_poll_run", "works_ingested_24h", "works_ingested_1h"):
        assert key in body["ingestion"], f"Missing ingestion key: {key}"

    for key in ("status", "redis_memory_used", "usrn_cache_hits"):
        assert key in body["cache"], f"Missing cache key: {key}"

    for key in ("phase", "modules_complete", "modules_total", "next_module"):
        assert key in body["phase"], f"Missing phase key: {key}"

    for key in ("api_version", "environment", "uptime_seconds"):
        assert key in body["system"], f"Missing system key: {key}"


def test_health_detail_phase_info() -> None:
    """Phase block must report Phase 1 metadata correctly."""
    with (
        patch("routers.health._db_health", AsyncMock(return_value=_DB_OK)),
        patch("routers.health._cache_health", AsyncMock(return_value=_CACHE_OK)),
        patch("routers.health._ingestion_health", AsyncMock(return_value=_INGESTION_OK)),
    ):
        resp = client.get("/health/detail")

    phase = resp.json()["phase"]
    assert phase["phase"] == 1
    assert phase["modules_complete"] == 7
    assert phase["modules_total"] == 8
    assert phase["next_module"] == "UN-001-prep"


def test_health_detail_response_time() -> None:
    """Endpoint must respond within 200ms when infrastructure is mocked."""
    with (
        patch("routers.health._db_health", AsyncMock(return_value=_DB_OK)),
        patch("routers.health._cache_health", AsyncMock(return_value=_CACHE_OK)),
        patch("routers.health._ingestion_health", AsyncMock(return_value=_INGESTION_OK)),
    ):
        start = time.monotonic()
        resp = client.get("/health/detail")
        elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 0.2, f"Response took {elapsed:.3f}s, expected < 0.2s"


def test_health_detail_status_field() -> None:
    """The status field must be one of the three valid values: ok, degraded, error."""
    valid = {"ok", "degraded", "error"}

    with (
        patch("routers.health._db_health", AsyncMock(return_value=_DB_OK)),
        patch("routers.health._cache_health", AsyncMock(return_value=_CACHE_OK)),
        patch("routers.health._ingestion_health", AsyncMock(return_value=_INGESTION_OK)),
    ):
        resp_ok = client.get("/health/detail")

    with (
        patch("routers.health._db_health", AsyncMock(return_value=_DB_OK)),
        patch("routers.health._cache_health", AsyncMock(return_value=_CACHE_OK)),
        patch("routers.health._ingestion_health", AsyncMock(return_value=_INGESTION_STALE)),
    ):
        resp_degraded = client.get("/health/detail")

    with (
        patch(
            "routers.health._db_health",
            AsyncMock(side_effect=Exception("DB down")),
        ),
        patch("routers.health._cache_health", AsyncMock(return_value=_CACHE_OK)),
        patch("routers.health._ingestion_health", AsyncMock(return_value=_INGESTION_OK)),
    ):
        resp_error = client.get("/health/detail")

    assert resp_ok.json()["status"] in valid
    assert resp_degraded.json()["status"] in valid
    assert resp_error.json()["status"] in valid
    assert resp_ok.json()["status"] == "ok"
    assert resp_degraded.json()["status"] == "degraded"
    assert resp_error.json()["status"] == "error"
