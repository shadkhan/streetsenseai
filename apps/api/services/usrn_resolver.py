"""SM-003 — USRN resolver via OS National Street Gazetteer API.

Resolves USRN codes to street metadata (name, town, authority, road class).
USRNs are stable identifiers — once assigned they never change — so results
are cached indefinitely in Redis with no TTL.

Gracefully returns None when OS_API_KEY is not configured, allowing the rest
of the pipeline to continue without street name enrichment.
"""
from __future__ import annotations

import logging

import httpx
from redis.asyncio import Redis
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from config import settings
from schemas.domain import USRNInfo
from schemas.os_api import OSNSGResponse

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "usrn:"
_OS_NSG_BASE = "https://api.os.uk/search/nsg/v1"


def _is_rate_limited(exc: BaseException) -> bool:
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429


def _parse_nsg_response(payload: dict) -> USRNInfo | None:
    """Parse the top-level OS NSG response dict into a USRNInfo domain object."""
    parsed = OSNSGResponse.model_validate(payload)
    if not parsed.results:
        return None

    first = parsed.results[0]
    descriptor = first.STREET_DESCRIPTOR
    street = first.STREET

    usrn = (descriptor.USRN if descriptor else None) or (street.USRN if street else None)
    street_description = descriptor.STREET_DESCRIPTION if descriptor else None

    if not usrn or not street_description:
        return None

    return USRNInfo(
        usrn=str(usrn),
        street_name=street_description.title(),
        locality=descriptor.LOCALITY_NAME if descriptor else None,
        town=descriptor.TOWN_NAME if descriptor else None,
        authority=descriptor.ADMINISTRATIVE_AREA if descriptor else None,
        road_classification=street.CLASSIFICATION if street else None,
    )


class USRNResolver:
    """Resolve USRN codes to street metadata via the OS NSG API.

    Usage (async context manager):
        async with USRNResolver(redis_client) as resolver:
            info = await resolver.resolve("41507223")

    Injectable http_client for testing — pass a MagicMock(spec=httpx.AsyncClient)
    to avoid Windows SSL initialisation in unit tests.
    """

    def __init__(
        self,
        redis_client: Redis,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._redis = redis_client
        self._http = http_client
        self._owns_http = http_client is None

    async def __aenter__(self) -> "USRNResolver":
        if self._owns_http:
            self._http = httpx.AsyncClient(timeout=10.0)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._owns_http and self._http is not None:
            await self._http.aclose()

    async def resolve(self, usrn: str) -> USRNInfo | None:
        """Resolve a single USRN. Returns None if not found or key not configured."""
        if not settings.os_api_key:
            logger.debug("OS_API_KEY not set — USRN resolution skipped for %s", usrn)
            return None

        cache_key = f"{_CACHE_PREFIX}{usrn}"
        cached = await self._redis.get(cache_key)
        if cached:
            return USRNInfo.model_validate_json(cached)

        info = await self._fetch(usrn)
        if info is not None:
            # No TTL — USRNs are permanent identifiers
            await self._redis.set(cache_key, info.model_dump_json())
        return info

    async def batch_resolve(self, usrns: list[str]) -> dict[str, USRNInfo]:
        """Resolve multiple USRNs concurrently. Returns only successfully resolved ones."""
        results: dict[str, USRNInfo] = {}
        for usrn in usrns:
            info = await self.resolve(usrn)
            if info is not None:
                results[usrn] = info
        return results

    @retry(
        retry=retry_if_exception(_is_rate_limited),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    async def _fetch(self, usrn: str) -> USRNInfo | None:
        assert self._http is not None
        response = await self._http.get(
            f"{_OS_NSG_BASE}/street",
            params={"usrn": usrn, "key": settings.os_api_key},
        )
        if response.status_code == 404:
            logger.debug("USRN %s not found in OS NSG", usrn)
            return None
        response.raise_for_status()  # raises HTTPStatusError for 4xx/5xx (triggers retry on 429)

        return _parse_nsg_response(response.json())
