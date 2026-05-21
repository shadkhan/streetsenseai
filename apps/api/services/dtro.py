"""DT-001 — D-TRO public beta data consumer (ADR-027).

Authentication: OAuth 2.0 client credentials flow (confirmed from official DfT Postman collection).
  - POST /oauth-generator with HTTP Basic Auth (DTRO_KEY:DTRO_SECRET)
    and form body grant_type=client_credentials → access_token
  - access_token valid for 30 minutes; cached in Redis for 25 minutes (5-min buffer)
  - Bearer token on all subsequent requests

Base URL includes the /v1 version prefix:
  - Integration: https://dtro-integration.dft.gov.uk/v1
  - Production:  https://dtro.dft.gov.uk/v1

Correct API paths (relative to base URL):
  - POST /oauth-generator       → get access token
  - GET  /dtros/all             → list all D-TROs
  - GET  /dtros/{id}            → get single D-TRO
  - POST /search                → search with query body

Three-mode data strategy (ADR-027):
  - Mode 1 (DTRO_KEY not set): synthetic fixture from dtro_generator.py
  - Mode 2 (credentials set, DTRO_BASE_URL=.../v1 integration): integration
  - Mode 3 (credentials set, DTRO_BASE_URL=.../v1 production): production

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

# Credential mapping:
#   DTRO_KEY     → HTTP Basic Auth username (OAuth2 client identifier)
#   DTRO_SECRET  → HTTP Basic Auth password
#   DTRO_APP_ID  → portal registration UUID — not used in OAuth2 flow
def _resolve_client_id() -> str:
    return settings.dtro_key or settings.dtro_app_id or settings.dtro_client_id

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
        # POST /oauth-generator — HTTP Basic Auth (apiKey:apiSecret) +
        # form body grant_type=client_credentials (DfT official Postman collection).
        resp = await self._http.post(
            "/oauth-generator",
            data={"grant_type": "client_credentials"},
            auth=(_resolve_client_id(), _resolve_client_secret()),
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        token: str = data.get("access_token") or data.get("token") or data.get("idToken", "")
        if not token:
            raise ValueError(f"No access_token in D-TRO auth response: {list(data.keys())}")
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
        self, page: int = 1, page_size: int = 100
    ) -> list[dict[str, Any]]:
        if self._use_synthetic:
            return []   # synthetic data lives in the DB via the seed endpoint
        data = await self._get("/dtros/all", params={"page": page, "pageSize": page_size})
        # Response shape: list directly, or wrapped in a key
        if isinstance(data, list):
            return data
        return data.get("dtros", data.get("tros", []))  # type: ignore[no-any-return]

    async def get_dtro_by_id(self, dtro_id: str) -> dict[str, Any]:
        data = await self._get(f"/dtros/{dtro_id}")
        return data  # type: ignore[return-value]

    async def _post(self, path: str, body: dict[str, Any]) -> Any:
        token = await self._auth.get_token()
        resp = await self._http.post(
            path,
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 401:
            await self._auth.invalidate()
            token = await self._auth.get_token()
            resp = await self._http.post(
                path,
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
        resp.raise_for_status()
        return resp.json()

    async def search_dtros(
        self,
        bbox: tuple[float, float, float, float] | None = None,
        tra_creator: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> list[dict[str, Any]]:
        """Search D-TROs via POST /search with a query body."""
        if self._use_synthetic:
            return []
        queries: list[dict[str, Any]] = []
        if tra_creator is not None:
            queries.append({"traCreator": tra_creator})
        if bbox is not None:
            queries.append({"bbox": list(bbox)})
        body: dict[str, Any] = {"page": page, "pageSize": page_size, "queries": queries}
        data = await self._post("/search", body)
        if isinstance(data, list):
            return data
        return data.get("dtros", data.get("tros", []))  # type: ignore[no-any-return]
