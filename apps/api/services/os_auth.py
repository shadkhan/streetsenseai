"""OS Data Hub OAuth 2.0 client-credentials token manager.

OS Data Hub migrated from a single API key to OAuth 2.0 in 2025.
Credentials live in .env.local as OS_CLIENT_ID (Project ID) and
OS_CLIENT_SECRET (Project Secret).

The access token is cached in Redis for (expires_in - 300) seconds so it
is refreshed 5 minutes before expiry without hammering the token endpoint.
Returns None gracefully when credentials are not configured, allowing callers
(USRNResolver, RoadClassifier) to skip enrichment without raising.
"""
from __future__ import annotations

import logging
from base64 import b64encode

import httpx
from redis.asyncio import Redis

from config import settings

logger = logging.getLogger(__name__)

_TOKEN_CACHE_KEY = "os_oauth_token"
_TOKEN_URL = "https://api.os.uk/oauth2/token/v1"
_TOKEN_TTL_BUFFER = 300  # seconds — refresh 5 min before expiry


async def get_os_token(
    redis_client: Redis,
    http_client: httpx.AsyncClient,
) -> str | None:
    """Return a valid OS Data Hub Bearer token.

    Checks Redis first; fetches and caches a new token on miss.
    Returns None if credentials are absent so callers can skip gracefully.
    """
    if not settings.os_client_id or not settings.os_client_secret:
        logger.debug("OS_CLIENT_ID/SECRET not configured — OS API calls will be skipped")
        return None

    cached = await redis_client.get(_TOKEN_CACHE_KEY)
    if cached is not None:
        return cached.decode() if isinstance(cached, bytes) else cached

    credentials = b64encode(
        f"{settings.os_client_id}:{settings.os_client_secret}".encode()
    ).decode()

    response = await http_client.post(
        _TOKEN_URL,
        headers={"Authorization": f"Basic {credentials}"},
        data={"grant_type": "client_credentials"},
    )
    response.raise_for_status()
    body = response.json()

    token: str = body["access_token"]
    expires_in: int = int(body.get("expires_in", 3600))
    ttl = max(expires_in - _TOKEN_TTL_BUFFER, 60)

    await redis_client.set(_TOKEN_CACHE_KEY, token, ex=ttl)
    logger.debug("Fetched new OS token, TTL=%ds", ttl)
    return token
