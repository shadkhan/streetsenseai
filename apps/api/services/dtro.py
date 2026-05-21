"""DT-001 — D-TRO public beta data consumer (ADR-027).

Authentication: OAuth 2.0 client credentials flow.
  - POST /v1/oauth-generator with client_id + client_secret → access_token
  - access_token valid for 30 minutes; cached in Redis for 25 minutes (5-min buffer)
  - Bearer token on all subsequent requests

Three-mode data strategy (ADR-027):
  - Mode 1 (DTRO_CLIENT_ID not set): synthetic fixture from dtro_generator.py
  - Mode 2 (credentials set, DTRO_BASE_URL=dtro-integration.dft.gov.uk): integration
  - Mode 3 (credentials set, DTRO_BASE_URL=dtro.dft.gov.uk): production

Fallback to synthetic is transparent to callers.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import httpx
from redis.asyncio import Redis

from config import settings

logger = logging.getLogger(__name__)

_TOKEN_KEY = "dtro:auth:access_token"
_TOKEN_TTL = 25 * 60   # 25-min Redis TTL (access token valid for 30 min)

# Resolve credentials — new names (DTRO_APP_ID/KEY/SECRET) take precedence over legacy aliases
def _resolve_client_id() -> str:
    return settings.dtro_app_id or settings.dtro_key or settings.dtro_client_id

def _resolve_client_secret() -> str:
    return settings.dtro_secret or settings.dtro_client_secret


class DTROAuthManager:
    """OAuth 2.0 client credentials token lifecycle for D-TRO API (ADR-027)."""

    def __init__(self, redis: Redis, http: httpx.AsyncClient | None = None) -> None:
        self._redis = redis
        self._http = http or httpx.AsyncClient(
            base_url=settings.dtro_base_url,
            timeout=15.0,
            headers={"Accept": "application/json"},
        )

    async def get_token(self) -> str:
        cached = await self._redis.get(_TOKEN_KEY)
        if cached:
            return cached.decode() if isinstance(cached, bytes) else cached  # type: ignore[return-value]
        return await self._authenticate()

    async def invalidate(self) -> None:
        await self._redis.delete(_TOKEN_KEY)

    async def _authenticate(self) -> str:
        resp = await self._http.post(
            "/v1/oauth-generator",
            json={
                "clientId": _resolve_client_id(),
                "clientSecret": _resolve_client_secret(),
            },
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        token: str = data["access_token"]
        await self._redis.setex(_TOKEN_KEY, _TOKEN_TTL, token)
        return token


class DTROClient:
    """D-TRO API consumer — queries the D-TRO REST API for TROs.

    Falls back to synthetic generator data when DTRO_CLIENT_ID is not configured.
    """

    def __init__(
        self,
        redis: Redis,
        http: httpx.AsyncClient | None = None,
        auth: DTROAuthManager | None = None,
    ) -> None:
        self._redis = redis
        self._http = http or httpx.AsyncClient(
            base_url=settings.dtro_base_url,
            timeout=30.0,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        self._auth = auth or DTROAuthManager(redis)
        self._use_synthetic = not bool(_resolve_client_id() and _resolve_client_secret())

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        token = await self._auth.get_token()
        resp = await self._http.get(
            path,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 401:
            await self._auth.invalidate()
            token = await self._auth.get_token()
            resp = await self._http.get(
                path,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
        resp.raise_for_status()
        return resp.json()

    async def get_all_dtros(
        self, page: int = 0, limit: int = 100
    ) -> list[dict[str, Any]]:
        if self._use_synthetic:
            return []   # synthetic data lives in the DB via the seed endpoint
        data = await self._get("/v1/tros", params={"page": page, "limit": limit})
        return data.get("tros", [])  # type: ignore[no-any-return]

    async def get_dtro_by_id(self, dtro_id: str) -> dict[str, Any]:
        data = await self._get(f"/v1/tros/{dtro_id}")
        return data  # type: ignore[return-value]

    async def search_dtros(
        self,
        bbox: tuple[float, float, float, float],
        dtro_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search D-TROs by bounding box and optional type filter."""
        if self._use_synthetic:
            return []
        params: dict[str, Any] = {
            "bbox": ",".join(str(v) for v in bbox),
        }
        if dtro_type:
            params["type"] = dtro_type
        data = await self._get("/v1/tros/search", params=params)
        return data.get("tros", [])  # type: ignore[no-any-return]
