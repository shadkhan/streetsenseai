"""SM-004 — Road classification via OS Open Roads (OGC Features API).

Given a StreetWork's USRN and geometry, queries the OS Open Roads
OpenRoads_RoadLink collection to determine road classification and carriageway
attributes needed for Phase 2 corridor risk scoring.

Cache policy: 24 hours by USRN — road classifications change infrequently
and the OS Open Roads dataset is updated quarterly.

Gracefully returns None when OS_API_KEY is not configured.
"""
from __future__ import annotations

import logging

import httpx
from redis.asyncio import Redis
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from config import settings
from schemas.domain import LineStringGeometry, PointGeometry, RoadInfo
from schemas.os_api import OSOpenRoadsCollection

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "road:"
_CACHE_TTL = 86_400  # 24 hours
_OS_FEATURES_BASE = "https://api.os.uk/features/v1"
_BBOX_DEGREES = 0.0005  # ~50 m at UK latitudes
_BBOX_CRS = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"

# Higher-priority classifications must sort first for best-match selection
_CLASSIFICATION_PRIORITY: dict[str, int] = {
    "Motorway": 0,
    "A Road": 1,
    "B Road": 2,
}
_PRIMARY_CLASSIFICATIONS = frozenset({"Motorway", "A Road"})


def _is_rate_limited(exc: BaseException) -> bool:
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429


def _representative_point(
    geometry: PointGeometry | LineStringGeometry,
) -> tuple[float, float]:
    """Return a single (lon, lat) representative of a geometry."""
    if isinstance(geometry, PointGeometry):
        return geometry.coordinates[0], geometry.coordinates[1]
    coords = geometry.coordinates
    mid = coords[len(coords) // 2]
    return mid[0], mid[1]


def _geometry_bbox(
    geometry: PointGeometry | LineStringGeometry,
    buffer: float = _BBOX_DEGREES,
) -> tuple[float, float, float, float]:
    """Return (minLon, minLat, maxLon, maxLat) WGS-84 bbox with a metre buffer."""
    if isinstance(geometry, PointGeometry):
        lon, lat = geometry.coordinates
        return lon - buffer, lat - buffer, lon + buffer, lat + buffer
    lons = [c[0] for c in geometry.coordinates]
    lats = [c[1] for c in geometry.coordinates]
    return min(lons) - buffer, min(lats) - buffer, max(lons) + buffer, max(lats) + buffer


def _parse_road_features(payload: dict) -> RoadInfo | None:
    """Extract the highest-priority RoadInfo from an OS Open Roads GeoJSON response.

    When multiple road links fall within the bbox (e.g. a junction), the one
    with the highest-priority classification (Motorway > A Road > B Road > other)
    is returned, matching Phase 2 corridor scoring expectations.
    """
    collection = OSOpenRoadsCollection.model_validate(payload)
    if not collection.features:
        return None

    sorted_features = sorted(
        collection.features,
        key=lambda f: _CLASSIFICATION_PRIORITY.get(
            (f.properties.road_classification if f.properties else None) or "",
            99,
        ),
    )

    props = sorted_features[0].properties
    if props is None:
        return None

    classification = props.road_classification or "Not Classified"
    return RoadInfo(
        road_classification=classification,
        road_function=props.road_function,
        road_name=props.name1,
        form_of_way=props.form_of_way,
        is_primary_route=classification in _PRIMARY_CLASSIFICATIONS,
    )


class RoadClassifier:
    """Classify a StreetWork's road type via OS Open Roads.

    Primary entry point: `classify_by_usrn(usrn, geometry)`.
    USRN is the cache key; geometry drives the spatial query on a cache miss.

    Usage (async context manager):
        async with RoadClassifier(redis_client) as classifier:
            info = await classifier.classify_by_usrn(work.usrn, work.geometry)

    Injectable http_client for testing — avoids Windows SSL init hang.
    """

    def __init__(
        self,
        redis_client: Redis,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._redis = redis_client
        self._http = http_client
        self._owns_http = http_client is None

    async def __aenter__(self) -> "RoadClassifier":
        if self._owns_http:
            self._http = httpx.AsyncClient(timeout=10.0)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._owns_http and self._http is not None:
            await self._http.aclose()

    async def classify_by_usrn(
        self,
        usrn: str,
        geometry: PointGeometry | LineStringGeometry,
    ) -> RoadInfo | None:
        """Return road classification for a USRN, fetching via geometry on cache miss."""
        if not settings.os_api_key:
            logger.debug("OS_API_KEY not set — road classification skipped for USRN %s", usrn)
            return None

        cache_key = f"{_CACHE_PREFIX}{usrn}"
        cached = await self._redis.get(cache_key)
        if cached:
            return RoadInfo.model_validate_json(cached)

        info = await self._fetch_by_geometry(geometry)
        if info is not None:
            await self._redis.set(cache_key, info.model_dump_json(), ex=_CACHE_TTL)
        return info

    @retry(
        retry=retry_if_exception(_is_rate_limited),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    async def _fetch_by_geometry(
        self,
        geometry: PointGeometry | LineStringGeometry,
    ) -> RoadInfo | None:
        assert self._http is not None
        min_lon, min_lat, max_lon, max_lat = _geometry_bbox(geometry)

        response = await self._http.get(
            f"{_OS_FEATURES_BASE}/collections/OpenRoads_RoadLink/items",
            params={
                "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
                "bbox-crs": _BBOX_CRS,
                "limit": 10,
                "key": settings.os_api_key,
            },
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()

        return _parse_road_features(response.json())
