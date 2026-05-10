"""Tests for OS Data Hub OAuth 2.0 token manager (os_auth.py)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.os_auth import _TOKEN_CACHE_KEY, _TOKEN_TTL_BUFFER, get_os_token


@pytest.fixture
def mock_redis() -> AsyncMock:
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)  # cache miss by default
    r.set = AsyncMock()
    return r


@pytest.fixture
def mock_http() -> MagicMock:
    return MagicMock(spec=httpx.AsyncClient)


def _token_response(token: str = "test-access-token", expires_in: int = 3600) -> MagicMock:
    r = MagicMock(spec=httpx.Response)
    r.status_code = 200
    r.json.return_value = {"access_token": token, "token_type": "Bearer", "expires_in": expires_in}
    r.raise_for_status = MagicMock()
    return r


# ── get_os_token — no credentials ─────────────────────────────────────────────

async def test_returns_none_when_client_id_missing(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    with patch("services.os_auth.settings") as s:
        s.os_client_id = ""
        s.os_client_secret = "secret"
        result = await get_os_token(mock_redis, mock_http)

    assert result is None
    mock_http.post.assert_not_called()


async def test_returns_none_when_client_secret_missing(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    with patch("services.os_auth.settings") as s:
        s.os_client_id = "my-project-id"
        s.os_client_secret = ""
        result = await get_os_token(mock_redis, mock_http)

    assert result is None
    mock_redis.get.assert_not_called()


# ── get_os_token — cache hit ───────────────────────────────────────────────────

async def test_returns_cached_token_as_string(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    mock_redis.get = AsyncMock(return_value=b"cached-token-value")

    with patch("services.os_auth.settings") as s:
        s.os_client_id = "pid"
        s.os_client_secret = "secret"
        result = await get_os_token(mock_redis, mock_http)

    assert result == "cached-token-value"
    mock_http.post.assert_not_called()


async def test_returns_cached_token_when_already_string(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    mock_redis.get = AsyncMock(return_value="string-token")

    with patch("services.os_auth.settings") as s:
        s.os_client_id = "pid"
        s.os_client_secret = "secret"
        result = await get_os_token(mock_redis, mock_http)

    assert result == "string-token"


# ── get_os_token — cache miss → token endpoint ────────────────────────────────

async def test_fetches_new_token_on_cache_miss(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    mock_http.post = AsyncMock(return_value=_token_response("fresh-token"))

    with patch("services.os_auth.settings") as s:
        s.os_client_id = "my-project-id"
        s.os_client_secret = "my-project-secret"
        result = await get_os_token(mock_redis, mock_http)

    assert result == "fresh-token"


async def test_uses_basic_auth_with_base64_credentials(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    import base64

    mock_http.post = AsyncMock(return_value=_token_response())

    with patch("services.os_auth.settings") as s:
        s.os_client_id = "my-id"
        s.os_client_secret = "my-secret"
        await get_os_token(mock_redis, mock_http)

    call_kwargs = mock_http.post.call_args.kwargs
    auth_header = call_kwargs["headers"]["Authorization"]
    assert auth_header.startswith("Basic ")
    decoded = base64.b64decode(auth_header[6:]).decode()
    assert decoded == "my-id:my-secret"


async def test_sends_client_credentials_grant_type(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    mock_http.post = AsyncMock(return_value=_token_response())

    with patch("services.os_auth.settings") as s:
        s.os_client_id = "pid"
        s.os_client_secret = "secret"
        await get_os_token(mock_redis, mock_http)

    call_kwargs = mock_http.post.call_args.kwargs
    assert call_kwargs["data"]["grant_type"] == "client_credentials"


async def test_caches_token_with_ttl_buffer(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    mock_http.post = AsyncMock(return_value=_token_response("tok", expires_in=3600))

    with patch("services.os_auth.settings") as s:
        s.os_client_id = "pid"
        s.os_client_secret = "secret"
        await get_os_token(mock_redis, mock_http)

    mock_redis.set.assert_called_once()
    key, value = mock_redis.set.call_args.args
    assert key == _TOKEN_CACHE_KEY
    assert value == "tok"
    assert mock_redis.set.call_args.kwargs["ex"] == 3600 - _TOKEN_TTL_BUFFER


async def test_short_expiry_clamped_to_minimum_60s(
    mock_redis: AsyncMock, mock_http: MagicMock
) -> None:
    mock_http.post = AsyncMock(return_value=_token_response(expires_in=120))

    with patch("services.os_auth.settings") as s:
        s.os_client_id = "pid"
        s.os_client_secret = "secret"
        await get_os_token(mock_redis, mock_http)

    ttl = mock_redis.set.call_args.kwargs["ex"]
    assert ttl >= 60
