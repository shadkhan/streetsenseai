"""CR-001 — OS Open Roads corridor geometry fetcher.

Queries the OS Features API (OpenRoads_RoadLink collection) for road
segments matching a named corridor, then merges them into a single
LineString using Shapely.

Falls back gracefully (returns None) when:
  - OS credentials are not configured
  - The API returns no matching road segments
  - The API returns a non-2xx status

Cache policy: 24 hours per corridor ID in Redis.
"""
from __future__ import annotations

import logging
import math

import httpx
from redis.asyncio import Redis
from shapely.geometry import MultiLineString
from shapely.geometry import LineString as ShapelyLineString
from shapely.ops import linemerge, unary_union
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from config import settings
from schemas.corridor import CorridorBase, RoadClassification
from schemas.domain import LineStringGeometry
from schemas.os_api import OSOpenRoadsCollection
from services.os_auth import get_os_token

logger = logging.getLogger(__name__)

_OS_FEATURES_BASE = "https://api.os.uk/features/v1"
_BBOX_CRS = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
_CACHE_PREFIX = "corridor:os:"
_CACHE_TTL = 86_400  # 24 hours
_KM_PER_DEG_LAT = 110.574

# Map OS classification strings to our domain values
_OS_CLASSIFICATION_MAP: dict[str, RoadClassification] = {
    "A Road": "A",
    "B Road": "B",
    "Motorway": "A",  # Motorways treated as A for Phase 2 scope
    "Unclassified": "unclassified",
    "Not Classified": "unclassified",
    "C Road": "C",
}


def _km_per_deg_lng(lat: float) -> float:
    return 111.32 * math.cos(math.radians(lat))


def _is_rate_limited(exc: BaseException) -> bool:
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429


class OSOpenRoadsClient:
    """Fetch and merge road corridor geometries from OS Open Roads.

    Injectable http_client for testing — avoids Windows SSL init hang.

    Usage:
        async with OSOpenRoadsClient(redis) as client:
            geom = await client.get_corridor_geometry(
                corridor_id="a38-birmingham",
                road_name="A38",
                centre_lng=-1.902,
                centre_lat=52.486,
                length_km=3.5,
            )
    """

    def __init__(
        self,
        redis_client: Redis,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._redis = redis_client
        self._http = http_client
        self._owns_http = http_client is None

    async def __aenter__(self) -> "OSOpenRoadsClient":
        if self._owns_http:
            self._http = httpx.AsyncClient(timeout=15.0)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._owns_http and self._http is not None:
            await self._http.aclose()

    async def get_corridor_geometry(
        self,
        corridor_id: str,
        road_name: str,
        centre_lng: float,
        centre_lat: float,
        length_km: float,
    ) -> LineStringGeometry | None:
        """Return a merged LineString for the named road near the given centre.

        Returns None if credentials are missing, the API returns no matching
        segments, or any network/HTTP error occurs.
        """
        if not settings.os_client_id:
            logger.debug("OS_CLIENT_ID not configured — skipping OS fetch for %s", corridor_id)
            return None

        cache_key = f"{_CACHE_PREFIX}{corridor_id}"
        cached = await self._redis.get(cache_key)
        if cached:
            return LineStringGeometry.model_validate_json(cached)

        geom = await self._fetch_geometry(road_name, centre_lng, centre_lat, length_km)
        if geom is not None:
            await self._redis.set(cache_key, geom.model_dump_json(), ex=_CACHE_TTL)
        return geom

    @retry(
        retry=retry_if_exception(_is_rate_limited),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    async def _fetch_geometry(
        self,
        road_name: str,
        centre_lng: float,
        centre_lat: float,
        length_km: float,
    ) -> LineStringGeometry | None:
        assert self._http is not None

        token = await get_os_token(self._redis, self._http)
        if token is None:
            return None

        # Expand bbox by 1.5 km beyond corridor ends on each side
        buffer_km = length_km / 2 + 1.5
        kdl = _km_per_deg_lng(centre_lat)
        min_lon = centre_lng - buffer_km / kdl
        max_lon = centre_lng + buffer_km / kdl
        min_lat = centre_lat - buffer_km / _KM_PER_DEG_LAT
        max_lat = centre_lat + buffer_km / _KM_PER_DEG_LAT

        response = await self._http.get(
            f"{_OS_FEATURES_BASE}/collections/OpenRoads_RoadLink/items",
            params={
                "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
                "bbox-crs": _BBOX_CRS,
                "limit": 100,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code in (401, 403, 404):
            logger.warning(
                "OS Open Roads returned %d for road=%s — check credentials/subscription",
                response.status_code,
                road_name,
            )
            return None

        response.raise_for_status()

        collection = OSOpenRoadsCollection.model_validate(response.json())

        # Filter to features that match the road name and have LineString geometry
        road_name_upper = road_name.upper()
        matching = [
            f for f in collection.features
            if f.geometry is not None
            and f.geometry.type == "LineString"
            and f.properties is not None
            and f.properties.name1 is not None
            and road_name_upper in f.properties.name1.upper()
        ]

        if not matching:
            logger.debug("OS Open Roads: no segments found for road=%s in bbox", road_name)
            return None

        # Merge all matching segments into a single LineString
        segments = [ShapelyLineString(f.geometry.coordinates) for f in matching]
        merged = linemerge(unary_union(segments))

        if merged.is_empty:
            return None

        # If merge produced a MultiLineString, take the longest contiguous segment
        if isinstance(merged, MultiLineString):
            merged = max(merged.geoms, key=lambda g: g.length)

        coords: list[tuple[float, float]] = [
            (round(c[0], 6), round(c[1], 6)) for c in merged.coords  # type: ignore[union-attr]
        ]

        logger.info(
            "OS Open Roads: %d segments merged for road=%s (%d vertices)",
            len(matching),
            road_name,
            len(coords),
        )
        return LineStringGeometry(type="LineString", coordinates=coords)

    async def build_corridor(
        self,
        corridor_id: str,
        name: str,
        road_name: str,
        road_classification: RoadClassification,
        centre_lng: float,
        centre_lat: float,
        length_km: float,
    ) -> CorridorBase | None:
        """Fetch geometry and return a CorridorBase, or None on failure."""
        geom = await self.get_corridor_geometry(
            corridor_id=corridor_id,
            road_name=road_name,
            centre_lng=centre_lng,
            centre_lat=centre_lat,
            length_km=length_km,
        )
        if geom is None:
            return None
        return CorridorBase(
            id=corridor_id,
            name=name,
            road_classification=road_classification,
            geometry=geom,
            source="os_open_roads",
        )
