"""Admin — lightweight probes for every external API used by StreetSense AI.

Each probe returns a dict with at minimum:
  status          : "ok" | "error" | "not_configured"
  response_time_ms: int
  status_code     : int | None
  response        : dict  (sanitised — never includes secrets)
  error           : str | None
"""
from __future__ import annotations

import time
from typing import Any

import httpx

from config import settings

# ── Anthropic pricing (USD per million tokens, May 2026) ──────────────────────
_ANTHROPIC_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-20250514":   {"input": 3.00,  "output": 15.00},
    "claude-haiku-4-5-20251001":  {"input": 0.80,  "output": 4.00},
}

# ── Mapbox pricing ─────────────────────────────────────────────────────────────
# Free tier: 100k geocoding calls/month; $0.50 per 1000 thereafter
_MAPBOX_FREE_TIER = 100_000


def _elapsed(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


async def probe_anthropic() -> dict[str, Any]:
    if not settings.anthropic_api_key:
        return {
            "status": "not_configured",
            "message": "ANTHROPIC_API_KEY not set",
            "response_time_ms": 0,
            "status_code": None,
        }
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Reply with just: OK"}],
                },
            )
        ms = _elapsed(start)
        data = resp.json()
        usage = data.get("usage", {})
        in_tok = usage.get("input_tokens", 0)
        out_tok = usage.get("output_tokens", 0)
        pricing = _ANTHROPIC_PRICING["claude-haiku-4-5-20251001"]
        cost_usd = (in_tok / 1_000_000 * pricing["input"]) + (out_tok / 1_000_000 * pricing["output"])
        return {
            "status": "ok" if resp.status_code == 200 else "error",
            "status_code": resp.status_code,
            "response_time_ms": ms,
            "response": {
                "model": data.get("model"),
                "content": data.get("content"),
                "stop_reason": data.get("stop_reason"),
            },
            "usage": {"input_tokens": in_tok, "output_tokens": out_tok},
            "cost": {
                "this_call_usd": round(cost_usd, 8),
                "model": "claude-haiku-4-5-20251001",
                "input_rate": f"${pricing['input']}/MTok",
                "output_rate": f"${pricing['output']}/MTok",
                "copilot_model_rate": f"${_ANTHROPIC_PRICING['claude-sonnet-4-20250514']['input']}/${_ANTHROPIC_PRICING['claude-sonnet-4-20250514']['output']} per MTok (Sonnet)",
            },
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc), "response_time_ms": _elapsed(start), "status_code": None}


_SM_AUTH_PATH = "/v3/party/authenticate"
_SM_WORKS_PATH = "/v7/works"

_SM_JSON_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}


async def probe_street_manager() -> dict[str, Any]:
    if not settings.sm_email or not settings.sm_password:
        return {
            "status": "not_configured",
            "message": "SM_EMAIL / SM_PASSWORD not set — JWT credentials required (ADR-026). Register at manage-roadworks.service.gov.uk",
            "response_time_ms": 0,
            "status_code": None,
        }

    auth_url = f"{settings.sm_base_url}{_SM_AUTH_PATH}"
    start = time.monotonic()
    try:
        # follow_redirects=False so we see 3xx redirects explicitly instead of
        # silently ending up at the frontend 404 page
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            auth_resp = await client.post(
                auth_url,
                headers=_SM_JSON_HEADERS,
                json={"email": settings.sm_email, "password": settings.sm_password},
            )
        ms_auth = _elapsed(start)

        content_type = auth_resp.headers.get("content-type", "")
        is_json = "application/json" in content_type
        is_html = "text/html" in content_type

        # Redirect → auth endpoint has moved
        if auth_resp.status_code in (301, 302, 307, 308):
            return {
                "status": "error",
                "status_code": auth_resp.status_code,
                "response_time_ms": ms_auth,
                "error": f"Auth endpoint redirected → {auth_resp.headers.get('location', '?')}. Auth URL may have changed.",
                "response": {"auth_url_tried": auth_url},
            }

        # HTML back → path not found on server (frontend 404 catch-all)
        if is_html or not is_json:
            return {
                "status": "error",
                "status_code": auth_resp.status_code,
                "response_time_ms": ms_auth,
                "error": (
                    f"Auth endpoint returned HTML (not JSON) — path not found on server. "
                    f"Tried: POST {auth_url}. "
                    "Check SM_BASE_URL and whether credentials are REST API credentials "
                    "or portal login credentials. Webhook delivery works independently."
                ),
                "response": {"auth_url_tried": auth_url, "content_type": content_type},
            }

        if auth_resp.status_code != 200:
            body: Any = {}
            try:
                body = auth_resp.json()
            except Exception:
                body = {"raw": auth_resp.text[:300]}
            return {
                "status": "error",
                "status_code": auth_resp.status_code,
                "response_time_ms": ms_auth,
                "error": "Authentication rejected",
                "response": body,
            }

        id_token: str = auth_resp.json().get("id_token", "")

        # Step 2: probe v7 works endpoint using the id_token header
        start2 = time.monotonic()
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            resp = await client.get(
                f"{settings.sm_base_url}{_SM_WORKS_PATH}",
                headers={"token": id_token, "Accept": "application/json"},
                params={"limit": 2},
            )
        ms_data = _elapsed(start2)
        try:
            resp_body: Any = resp.json()
        except Exception:
            resp_body = {"raw": resp.text[:500]}
        return {
            "status": "ok" if resp.status_code == 200 else "error",
            "status_code": resp.status_code,
            "response_time_ms": ms_auth + ms_data,
            "response": resp_body,
            "cost": {
                "note": "Free UK government open data — no usage charges",
                "auth_ms": ms_auth,
                "data_ms": ms_data,
            },
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc), "response_time_ms": _elapsed(start), "status_code": None}


async def probe_os_datahub() -> dict[str, Any]:
    if not settings.os_client_id or not settings.os_client_secret:
        return {
            "status": "not_configured",
            "message": "OS_CLIENT_ID or OS_CLIENT_SECRET not set — free tier 1M transactions/month at osdatahub.os.uk",
            "response_time_ms": 0,
            "status_code": None,
        }
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(
                "https://api.os.uk/oauth2/token/v1",
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.os_client_id,
                    "client_secret": settings.os_client_secret,
                },
            )
        ms_auth = _elapsed(start)
        if token_resp.status_code != 200:
            return {
                "status": "error",
                "status_code": token_resp.status_code,
                "response_time_ms": ms_auth,
                "response": token_resp.json(),
            }
        token = token_resp.json().get("access_token", "")

        # Quick NSG lookup for a known Birmingham USRN
        start2 = time.monotonic()
        async with httpx.AsyncClient(timeout=15.0) as client:
            nsg_resp = await client.get(
                "https://api.os.uk/search/names/v1/find",
                headers={"Authorization": f"Bearer {token}"},
                params={"query": "Birmingham City Centre", "maxresults": 1},
            )
        ms_nsg = _elapsed(start2)
        body: Any = {}
        try:
            body = nsg_resp.json()
        except Exception:
            body = {"raw": nsg_resp.text[:500]}
        return {
            "status": "ok" if nsg_resp.status_code == 200 else "error",
            "status_code": nsg_resp.status_code,
            "response_time_ms": ms_auth + ms_nsg,
            "response": body,
            "cost": {
                "note": "Free tier: 1M transactions/month via OS Data Hub",
                "auth_ms": ms_auth,
                "query_ms": ms_nsg,
            },
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc), "response_time_ms": _elapsed(start), "status_code": None}


async def probe_mapbox() -> dict[str, Any]:
    token = settings.next_public_mapbox_token
    if not token:
        return {
            "status": "not_configured",
            "message": "NEXT_PUBLIC_MAPBOX_TOKEN not set — free tier 50k map loads/month at mapbox.com",
            "response_time_ms": 0,
            "status_code": None,
        }
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"https://api.mapbox.com/geocoding/v5/mapbox.places/Birmingham.json",
                params={"access_token": token, "country": "gb", "limit": 1},
            )
        ms = _elapsed(start)
        body: Any = {}
        try:
            body = resp.json()
            # Return just the first feature to keep output readable
            features = body.get("features", [])
            body = {"features_returned": len(features), "first": features[0] if features else None}
        except Exception:
            body = {"raw": resp.text[:500]}
        return {
            "status": "ok" if resp.status_code == 200 else "error",
            "status_code": resp.status_code,
            "response_time_ms": ms,
            "response": body,
            "cost": {
                "note": "Free tier: 100k geocoding calls/month; $0.50 per 1,000 thereafter",
                "map_loads_free_tier": "50k/month",
                "tiles_free_tier": "200k/month",
            },
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc), "response_time_ms": _elapsed(start), "status_code": None}


async def probe_nuar() -> dict[str, Any]:
    nuar_key = getattr(settings, "nuar_api_key", "")
    if not nuar_key:
        return {
            "status": "not_configured",
            "message": "NUAR_API_KEY not set — access restricted to authorised utility owners and local authorities. Apply at nuar.uk. Synthetic data active for Phase 4.",
            "response_time_ms": 0,
            "status_code": None,
        }
    # Key is set — attempt a token check
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{getattr(settings, 'nuar_base_url', 'https://api.nuar.uk')}/health",
                headers={"Authorization": f"Bearer {nuar_key}"},
            )
        return {
            "status": "ok" if resp.status_code < 400 else "error",
            "status_code": resp.status_code,
            "response_time_ms": _elapsed(start),
            "response": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"text": resp.text[:500]},
            "cost": {"note": "Free for authorised users under NUAR access agreement"},
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc), "response_time_ms": _elapsed(start), "status_code": None}


async def probe_dtro() -> dict[str, Any]:
    from services.dtro import _resolve_client_id, _resolve_client_secret
    client_id = _resolve_client_id()
    client_secret = _resolve_client_secret()
    if not client_id or not client_secret:
        return {
            "status": "not_configured",
            "message": (
                "DTRO_APP_ID / DTRO_KEY and DTRO_SECRET not set — "
                "add credentials from DfT D-TRO portal to .env.local. "
                "Synthetic D-TRO data is active (700 orders seeded via /dtros/admin/seed)."
            ),
            "response_time_ms": 0,
            "status_code": None,
        }
    base_url = settings.dtro_base_url or "https://dtro-integration.dft.gov.uk"
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=15.0) as client:
            token_resp = await client.post(
                "/v1/oauth-generator",
                json={"clientId": client_id, "clientSecret": client_secret},
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
        ms_auth = _elapsed(start)
        if token_resp.status_code != 200:
            body: Any = {}
            try:
                body = token_resp.json()
            except Exception:
                body = {"raw": token_resp.text[:300]}
            return {
                "status": "error",
                "status_code": token_resp.status_code,
                "response_time_ms": ms_auth,
                "error": "OAuth2 token request rejected",
                "response": body,
            }
        token: str = token_resp.json().get("access_token", "")
        # Probe the TROs list endpoint with the token
        start2 = time.monotonic()
        async with httpx.AsyncClient(base_url=base_url, timeout=15.0) as client:
            tros_resp = await client.get(
                "/v1/tros",
                params={"page": 0, "limit": 2},
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
        ms_data = _elapsed(start2)
        body2: Any = {}
        try:
            body2 = tros_resp.json()
        except Exception:
            body2 = {"raw": tros_resp.text[:500]}
        return {
            "status": "ok" if tros_resp.status_code == 200 else "error",
            "status_code": tros_resp.status_code,
            "response_time_ms": ms_auth + ms_data,
            "response": body2,
            "cost": {
                "note": "DfT D-TRO public beta — no usage charges",
                "auth_ms": ms_auth,
                "data_ms": ms_data,
                "base_url": base_url,
            },
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc), "response_time_ms": _elapsed(start), "status_code": None}


async def check_all() -> dict[str, Any]:
    """Run all probes concurrently and return a map of service → result."""
    import asyncio
    results = await asyncio.gather(
        probe_anthropic(),
        probe_street_manager(),
        probe_os_datahub(),
        probe_mapbox(),
        probe_nuar(),
        probe_dtro(),
        return_exceptions=True,
    )
    keys = ["anthropic", "street_manager", "os_datahub", "mapbox", "nuar", "dtro"]
    return {
        key: result if not isinstance(result, Exception) else {"status": "error", "error": str(result)}
        for key, result in zip(keys, results)
    }
