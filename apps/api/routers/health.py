"""SM-007 -- /health/detail comprehensive health endpoint.

GET /health/detail
  Returns database, ingestion pipeline, Redis cache, Phase 1 status,
  and system metrics. Used for Phase 1 success criteria monitoring
  (uptime > 99% over a 7-day rolling window).

Overall status rules:
  "error"    -- database unreachable
  "degraded" -- Redis unreachable OR last_webhook_received > 20 minutes ago
  "ok"       -- all sub-checks pass and ingestion is current
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db, get_redis
from models.street_work import StreetWork as StreetWorkRow

router = APIRouter(prefix="/health", tags=["health"])

_START_TIME: float = time.monotonic()
_STALE_SECONDS = 20 * 60  # 20 minutes

_LAST_WEBHOOK_KEY = "sm:last_webhook_received"
_LAST_POLL_KEY = "sm:last_poll_run"
_USRN_HITS_KEY = "sm:usrn_cache_hits"


# ── Sub-check helpers (module-level so tests can patch them) ───────────────────

async def _db_health(session: AsyncSession) -> dict[str, Any]:
    postgis_row = (await session.execute(text("SELECT PostGIS_version()"))).scalar()
    postgis_version = str(postgis_row) if postgis_row is not None else "unknown"

    total = (
        await session.execute(select(func.count()).select_from(StreetWorkRow))
    ).scalar_one()

    recent_row = (
        await session.execute(
            select(StreetWorkRow)
            .order_by(StreetWorkRow.updated_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return {
        "status": "ok",
        "total_works": int(total),
        "most_recent_permit": {
            "reference": recent_row.permit_reference,
            "timestamp": recent_row.updated_at.isoformat(),
        }
        if recent_row is not None
        else None,
        "postgis_version": postgis_version,
    }


async def _ingestion_health(
    session: AsyncSession,
    r: aioredis.Redis,
) -> dict[str, Any]:
    last_webhook_raw = await r.get(_LAST_WEBHOOK_KEY)
    last_webhook = last_webhook_raw.decode() if last_webhook_raw else None

    last_poll_raw = await r.get(_LAST_POLL_KEY)
    last_poll = last_poll_raw.decode() if last_poll_raw else None

    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)
    cutoff_1h = now - timedelta(hours=1)

    works_24h = (
        await session.execute(
            select(func.count())
            .select_from(StreetWorkRow)
            .where(StreetWorkRow.updated_at >= cutoff_24h)
        )
    ).scalar_one()

    works_1h = (
        await session.execute(
            select(func.count())
            .select_from(StreetWorkRow)
            .where(StreetWorkRow.updated_at >= cutoff_1h)
        )
    ).scalar_one()

    return {
        "last_webhook_received": last_webhook,
        "last_poll_run": last_poll,
        "works_ingested_24h": int(works_24h),
        "works_ingested_1h": int(works_1h),
    }


async def _cache_health(r: aioredis.Redis) -> dict[str, Any]:
    info: dict[str, Any] = await r.info("memory")
    used_memory = info.get("used_memory_human", "unknown")

    hits_raw = await r.get(_USRN_HITS_KEY)
    usrn_hits = int(hits_raw) if hits_raw else 0

    return {
        "status": "ok",
        "redis_memory_used": str(used_memory),
        "usrn_cache_hits": usrn_hits,
    }


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.get("/detail")
async def health_detail(
    session: AsyncSession = Depends(get_db),
    r: aioredis.Redis = Depends(get_redis),
) -> dict[str, Any]:
    ts = datetime.now(timezone.utc).isoformat()

    db_ok = True
    db_data: dict[str, Any] = {"status": "ok"}
    try:
        db_data = await _db_health(session)
    except Exception as exc:
        db_ok = False
        db_data = {"status": "error", "error": str(exc)}

    cache_ok = True
    cache_data: dict[str, Any] = {"status": "ok"}
    try:
        cache_data = await _cache_health(r)
    except Exception as exc:
        cache_ok = False
        cache_data = {"status": "error", "error": str(exc)}

    ingestion_ok = True
    ingestion_data: dict[str, Any] = {}
    try:
        ingestion_data = await _ingestion_health(session, r)
    except Exception as exc:
        ingestion_ok = False
        ingestion_data = {"status": "error", "error": str(exc)}

    # Staleness: degrade if webhook was never received or is > 20 min old
    stale = False
    if ingestion_ok:
        last_webhook = ingestion_data.get("last_webhook_received")
        if last_webhook is None:
            stale = True
        else:
            age = (
                datetime.now(timezone.utc) - datetime.fromisoformat(last_webhook)
            ).total_seconds()
            stale = age > _STALE_SECONDS
    else:
        stale = True

    if not db_ok:
        overall: str = "error"
    elif not cache_ok or stale:
        overall = "degraded"
    else:
        overall = "ok"

    return {
        "status": overall,
        "timestamp": ts,
        "database": db_data,
        "ingestion": ingestion_data,
        "cache": cache_data,
        "phase": {
            "phase": 1,
            "modules_complete": 7,
            "modules_total": 8,
            "next_module": "UN-001-prep",
        },
        "system": {
            "api_version": "0.1.0",
            "environment": settings.environment,
            "uptime_seconds": int(time.monotonic() - _START_TIME),
        },
    }
