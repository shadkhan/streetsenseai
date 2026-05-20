"""Street Manager Open Data API v7 client.

Authentication: JWT username/password (ADR-026).
  - POST /v3/party/authenticate → {id_token, access_token, refresh_token}
  - id_token passed as "token" header (NOT "Authorization: Bearer")
  - id_token cached in Redis for 55 minutes (5-min buffer before 1-hour expiry)
  - On 401: invalidate cached token, call /v3/party/refresh, retry once

Consumed by:
  - services/sqs_consumer.py  (SM-001 — event-driven ingestion)
  - tasks/ingest.py            (SM-005 — 15-minute polling fallback)
  - routers/works.py           (SM-006 — query endpoints)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import httpx
from redis.asyncio import Redis
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from config import settings
from schemas.domain import (
    LineStringGeometry,
    PointGeometry,
    RiskLevel,
    StreetWork,
    StreetWorkStatus,
)
from schemas.street_manager import SMPermitV7, SMWorksListV7

logger = logging.getLogger(__name__)

_SM_API_VERSION = "v7"
_PERMIT_CACHE_TTL = 300   # 5-minute minimum per CLAUDE.md §7
_BBOX_CACHE_TTL = 60      # 1 minute — bbox results are more volatile


# ── Retry predicate ────────────────────────────────────────────────────────────

def _is_rate_limited(exc: BaseException) -> bool:
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429


# ── Status normalisation ───────────────────────────────────────────────────────

_STATUS_MAP: dict[str, StreetWorkStatus] = {
    "submitted": "submitted",
    "granted": "granted",
    "permit_modification_request": "permit_modification_request",
    "refused": "refused",
    "revoked": "revoked",
    "in_progress": "in_progress",
    "completed": "completed",
    "closed": "closed",
}


# ── Auth Manager ───────────────────────────────────────────────────────────────

class StreetManagerAuthManager:
    """JWT authentication manager for the Street Manager API.

    Caches the id_token in Redis with a 55-minute TTL (5-minute buffer before
    the server-side 1-hour expiry). On cache miss, authenticates with email/password
    or refreshes using the stored refresh_token if one is available.

    SM auth endpoints are at /v3/party/* — different from the v7 data endpoints.
    """

    _CACHE_KEY = "sm:auth:id_token"
    _REFRESH_KEY = "sm:auth:refresh_token"
    _TOKEN_TTL = 55 * 60          # 55 minutes in seconds
    _REFRESH_TTL = 24 * 60 * 60   # 24-hour soft expiry for refresh tokens

    def __init__(
        self,
        redis: Redis,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self._redis = redis
        # Separate client for /v3 auth calls — no base_url, uses full URLs
        self._http = http or httpx.AsyncClient(timeout=15.0)

    async def get_token(self) -> str:
        """Return a valid id_token, authenticating or refreshing as needed."""
        raw = await self._redis.get(self._CACHE_KEY)
        if raw:
            return raw.decode() if isinstance(raw, bytes) else raw

        # Try refresh before falling back to full re-auth
        raw_refresh = await self._redis.get(self._REFRESH_KEY)
        if raw_refresh:
            refresh_token = raw_refresh.decode() if isinstance(raw_refresh, bytes) else raw_refresh
            try:
                return await self._refresh(refresh_token)
            except Exception as exc:
                logger.warning("SM token refresh failed, re-authenticating: %s", exc)

        return await self._authenticate()

    async def invalidate(self) -> None:
        """Delete the cached id_token so the next get_token() call fetches a new one."""
        await self._redis.delete(self._CACHE_KEY)

    async def _authenticate(self) -> str:
        resp = await self._http.post(
            f"{settings.sm_base_url}/v3/party/authenticate",
            json={"email": settings.sm_email, "password": settings.sm_password},
        )
        resp.raise_for_status()
        data = resp.json()
        id_token: str = data["id_token"]
        await self._redis.setex(self._CACHE_KEY, self._TOKEN_TTL, id_token)
        if refresh_token := data.get("refresh_token"):
            await self._redis.setex(self._REFRESH_KEY, self._REFRESH_TTL, refresh_token)
        logger.debug("SM authentication successful, token cached for %ds", self._TOKEN_TTL)
        return id_token

    async def _refresh(self, refresh_token: str) -> str:
        resp = await self._http.post(
            f"{settings.sm_base_url}/v3/party/refresh",
            json={"refresh_token": refresh_token},
        )
        resp.raise_for_status()
        data = resp.json()
        id_token: str = data["id_token"]
        await self._redis.setex(self._CACHE_KEY, self._TOKEN_TTL, id_token)
        # Store the new refresh token (rotation); fall back to the old one if not returned
        new_refresh = data.get("refresh_token", refresh_token)
        await self._redis.setex(self._REFRESH_KEY, self._REFRESH_TTL, new_refresh)
        logger.debug("SM token refreshed and cached for %ds", self._TOKEN_TTL)
        return id_token


# ── Normalisation ──────────────────────────────────────────────────────────────

def normalize_permit(raw: dict[str, Any]) -> StreetWork | None:
    """Normalise a Street Manager API v7 permit dict to a domain StreetWork.

    Returns None if the permit is missing required geometry or fails validation.
    All invalid permits are logged at WARNING level — callers should not raise.
    """
    try:
        permit = SMPermitV7.model_validate(raw)
    except Exception as exc:
        logger.warning("SM permit validation failed: %s", exc)
        return None

    if permit.geometry is None:
        logger.debug("Skipping %s — no geometry", raw.get("permit_reference_number"))
        return None

    geo_type = permit.geometry.type
    coords = permit.geometry.coordinates

    if geo_type == "Point":
        # GeoJSON Point: coordinates is [lng, lat]
        if len(coords) < 2:
            logger.warning("Point geometry has fewer than 2 coordinates: %s", coords)
            return None
        geometry: PointGeometry | LineStringGeometry = PointGeometry(
            type="Point",
            coordinates=(float(coords[0]), float(coords[1])),
        )
    elif geo_type == "LineString":
        # GeoJSON LineString: coordinates is [[lng, lat], ...]
        if len(coords) < 2:
            logger.warning("LineString geometry has fewer than 2 points: %s", coords)
            return None
        geometry = LineStringGeometry(
            type="LineString",
            coordinates=[(float(c[0]), float(c[1])) for c in coords],
        )
    else:
        logger.warning(
            "Unsupported geometry type '%s' for permit %s",
            geo_type,
            permit.permit_reference_number,
        )
        return None

    status: StreetWorkStatus = _STATUS_MAP.get(permit.permit_status.lower(), "submitted")

    return StreetWork(
        permit_reference=permit.permit_reference_number,
        usrn=str(permit.usrn),
        street_name=permit.street_name,
        authority=permit.area_name,
        promoter=permit.promoter_organisation,
        promoter_licence_number=permit.promoter_swa_code,
        work_type=permit.work_category,
        traffic_management_type=permit.traffic_management_type,
        restriction_type=permit.restriction_type,
        proposed_start_date=permit.proposed_start_date,
        proposed_end_date=permit.proposed_end_date,
        actual_start_date=permit.actual_start_date_time,
        actual_end_date=permit.actual_end_date_time,
        status=status,
        geometry=geometry,
    )


# ── Client ─────────────────────────────────────────────────────────────────────

class StreetManagerClient:
    """Async HTTP client for the Street Manager Open Data API v7.

    All requests carry the "token" header (SM's name for the id_token — not
    "Authorization: Bearer"). The auth manager handles token lifecycle.

    Usage (FastAPI dependency injection — wired in SM-006):
        client = StreetManagerClient(redis)
        work = await client.get_work("WG7/2025/04001234")
        await client.close()

    Or as an async context manager (preferred in tests):
        async with StreetManagerClient(redis) as client:
            work = await client.get_work(...)
    """

    def __init__(
        self,
        redis_client: Redis,
        http_client: httpx.AsyncClient | None = None,
        auth_manager: StreetManagerAuthManager | None = None,
    ) -> None:
        self._redis = redis_client
        # http_client can be injected for testing to avoid real SSL initialisation
        self._http = http_client or httpx.AsyncClient(
            base_url=f"{settings.sm_base_url}/{_SM_API_VERSION}",
            headers={"Accept": "application/json"},
            timeout=30.0,
        )
        self._auth = auth_manager or StreetManagerAuthManager(
            redis=redis_client,
            http=self._http,
        )

    async def __aenter__(self) -> StreetManagerClient:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def close(self) -> None:
        await self._http.aclose()

    # ── HTTP ───────────────────────────────────────────────────────────────────

    @retry(
        retry=retry_if_exception(_is_rate_limited),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        token = await self._auth.get_token()
        response = await self._http.get(path, params=params, headers={"token": token})
        if response.status_code == 401:
            # Token rejected — invalidate cache, refresh, retry once
            await self._auth.invalidate()
            token = await self._auth.get_token()
            response = await self._http.get(path, params=params, headers={"token": token})
        response.raise_for_status()
        return response.json()

    # ── Cache ──────────────────────────────────────────────────────────────────

    async def _cache_get(self, key: str) -> Any:
        raw = await self._redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def _cache_set(self, key: str, value: Any, ttl: int = _PERMIT_CACHE_TTL) -> None:
        await self._redis.setex(key, ttl, json.dumps(value, default=str))

    # ── Public API ─────────────────────────────────────────────────────────────

    async def get_work(self, permit_reference: str) -> StreetWork | None:
        """Fetch a single permit by reference. Cached for 5 minutes.

        SM v7 path: GET /works/{works_ref}/permits/{permit_ref}
        For most permits works_ref == permit_ref; modifications share the
        works_ref but have distinct permit_refs (TODO: handle in SM-006).
        """
        cache_key = f"sm:permit:{permit_reference}"
        if cached := await self._cache_get(cache_key):
            return normalize_permit(cached)

        try:
            data = await self._get(
                f"/works/{permit_reference}/permits/{permit_reference}"
            )
            await self._cache_set(cache_key, data)
            return normalize_permit(data)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise

    async def get_works_by_bbox(
        self,
        bbox: tuple[float, float, float, float],
        status: list[str] | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        cursor: str | None = None,
    ) -> tuple[list[StreetWork], str | None]:
        """Fetch works within a bounding box [min_lon, min_lat, max_lon, max_lat].

        Returns (works, next_cursor). next_cursor is None when no more pages exist.
        Cached for 1 minute (shorter TTL than permits — spatial results change faster).
        """
        min_lon, min_lat, max_lon, max_lat = bbox
        cache_key = (
            f"sm:bbox:{min_lon:.4f},{min_lat:.4f},{max_lon:.4f},{max_lat:.4f}"
            f":s={'|'.join(status or [])}"
            f":f={from_date.isoformat() if from_date else ''}"
            f":c={cursor or ''}"
        )

        if cached := await self._cache_get(cache_key):
            works_raw: list[dict[str, Any]] = cached.get("works", [])
            next_cursor: str | None = cached.get("pagination_cursor")
            return [w for raw in works_raw if (w := normalize_permit(raw)) is not None], next_cursor

        params: dict[str, Any] = {
            "bounding_box": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        }
        if status:
            params["permit_status"] = ",".join(status)
        if from_date:
            params["works_actuals_from"] = from_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        if to_date:
            params["works_actuals_to"] = to_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        if cursor:
            params["pagination_cursor"] = cursor

        data = await self._get("/works", params=params)
        await self._cache_set(cache_key, data, ttl=_BBOX_CACHE_TTL)

        list_response = SMWorksListV7.model_validate(data)
        works = [
            w
            for permit in list_response.works
            if (w := normalize_permit(permit.model_dump())) is not None
        ]
        return works, list_response.pagination_cursor

    async def get_works_since(self, since: datetime) -> list[StreetWork]:
        """Fetch all works updated since `since`.

        Used by the SM-005 15-minute polling fallback (tasks/ingest.py).
        Cached for the standard 5-minute TTL.
        """
        cache_key = f"sm:since:{since.isoformat()}"
        if cached := await self._cache_get(cache_key):
            return [w for raw in cached if (w := normalize_permit(raw)) is not None]

        params: dict[str, Any] = {
            "works_actuals_from": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        data = await self._get("/works", params=params)
        list_response = SMWorksListV7.model_validate(data)
        raw_list = [p.model_dump() for p in list_response.works]
        await self._cache_set(cache_key, raw_list)
        return [w for raw in raw_list if (w := normalize_permit(raw)) is not None]
