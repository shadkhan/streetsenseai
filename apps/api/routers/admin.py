"""Admin endpoints — API health, data source config, system stats.

All endpoints under /admin prefix.
Protected in production by X-Admin-Key header matching ADMIN_API_KEY env var.
In development (ADMIN_API_KEY not set) protection is skipped.
"""
from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db, get_redis
from models.street_work import StreetWork as StreetWorkRow
from services import api_health
from services.data_source_config import DataSourceConfig, get_config, save_config

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Auth dependency ────────────────────────────────────────────────────────────

async def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    expected = getattr(settings, "admin_api_key", "")
    if expected and x_admin_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Key header")


# ── API Health ─────────────────────────────────────────────────────────────────

@router.get("/api-health", summary="Probe all external API connections")
async def get_api_health(_: None = Depends(require_admin)) -> dict[str, Any]:
    return await api_health.check_all()


SERVICE_PROBES = {
    "anthropic":      api_health.probe_anthropic,
    "street_manager": api_health.probe_street_manager,
    "os_datahub":     api_health.probe_os_datahub,
    "mapbox":         api_health.probe_mapbox,
    "nuar":           api_health.probe_nuar,
}


@router.post("/api-test/{service}", summary="Run a live test call to a named external service")
async def test_service(
    service: str,
    _: None = Depends(require_admin),
) -> dict[str, Any]:
    probe = SERVICE_PROBES.get(service)
    if not probe:
        raise HTTPException(status_code=404, detail=f"Unknown service '{service}'. Valid: {list(SERVICE_PROBES)}")
    try:
        return await probe()
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ── Data Source Config ─────────────────────────────────────────────────────────

@router.get("/data-source", summary="Get current data source mode configuration")
async def get_data_source(
    r: aioredis.Redis = Depends(get_redis),
    _: None = Depends(require_admin),
) -> DataSourceConfig:
    return await get_config(r)


@router.post("/data-source", summary="Update data source mode configuration")
async def update_data_source(
    config: DataSourceConfig,
    r: aioredis.Redis = Depends(get_redis),
    _: None = Depends(require_admin),
) -> DataSourceConfig:
    await save_config(r, config)
    return config


# ── System Stats ───────────────────────────────────────────────────────────────

@router.get("/stats", summary="Database record counts and system info")
async def get_stats(
    session: AsyncSession = Depends(get_db),
    r: aioredis.Redis = Depends(get_redis),
    _: None = Depends(require_admin),
) -> dict[str, Any]:
    # Street works counts
    total_works = (await session.execute(select(func.count()).select_from(StreetWorkRow))).scalar_one()

    active_works = (
        await session.execute(
            select(func.count()).select_from(StreetWorkRow).where(StreetWorkRow.status == "in_progress")
        )
    ).scalar_one()

    # Works by status
    status_rows = (
        await session.execute(
            select(StreetWorkRow.status, func.count().label("n"))
            .group_by(StreetWorkRow.status)
            .order_by(func.count().desc())
        )
    ).all()
    by_status = {row.status: row.n for row in status_rows}

    # Corridors
    try:
        from models.corridor import Corridor as CorridorRow
        total_corridors = (await session.execute(select(func.count()).select_from(CorridorRow))).scalar_one()
        scored_corridors = (
            await session.execute(
                select(func.count()).select_from(CorridorRow).where(CorridorRow.risk_score.isnot(None))
            )
        ).scalar_one()
    except Exception:
        total_corridors = scored_corridors = 0

    # NUAR assets
    try:
        from models.nuar import NUARAsset as NUARRow
        total_nuar = (await session.execute(select(func.count()).select_from(NUARRow))).scalar_one()
    except Exception:
        total_nuar = 0

    # Audit logs
    try:
        from models.audit import AIAuditLog as AuditRow
        total_audit = (await session.execute(select(func.count()).select_from(AuditRow))).scalar_one()
    except Exception:
        total_audit = 0

    # Redis info
    redis_info: dict[str, Any] = {}
    try:
        mem = await r.info("memory")
        redis_info = {
            "used_memory_human": mem.get("used_memory_human"),
            "connected_clients": (await r.info("clients")).get("connected_clients"),
        }
    except Exception:
        redis_info = {"status": "unavailable"}

    # Data source config
    ds_config = await get_config(r)

    return {
        "street_works": {
            "total": int(total_works),
            "active": int(active_works),
            "by_status": by_status,
        },
        "corridors": {
            "total": int(total_corridors),
            "scored": int(scored_corridors),
        },
        "nuar_assets": {"total": int(total_nuar)},
        "audit_logs": {"total": int(total_audit)},
        "redis": redis_info,
        "data_source_config": ds_config.model_dump(),
        "environment": settings.environment,
        "phase": 5,
        "api_keys_configured": {
            "anthropic": bool(settings.anthropic_api_key),
            "street_manager": bool(settings.street_manager_api_key),
            "os_datahub": bool(settings.os_client_id and settings.os_client_secret),
            "mapbox": bool(settings.next_public_mapbox_token),
            "nuar": bool(getattr(settings, "nuar_api_key", "")),
        },
    }
