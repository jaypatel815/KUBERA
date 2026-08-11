"""Shared httpx plumbing for Alpaca REST clients (T017).

Pure refactor target: both `data/alpaca.py` and `data/market_data.py` build the same
authenticated client and apply the same error discipline. Error TEXT stays exactly what
each client used before — the existing test suite is the contract.
"""

import httpx

from settings import KuberaSettings

TIMEOUT_SECONDS = 15.0


def build_client(
    base_url: str,
    settings: KuberaSettings,
    transport: httpx.BaseTransport | None = None,
) -> httpx.Client:
    """Authenticated Alpaca client. Caller must have run settings.require_alpaca()."""
    assert settings.alpaca_api_secret_key is not None  # guaranteed by require_alpaca()
    return httpx.Client(
        base_url=base_url,
        headers={
            "APCA-API-KEY-ID": settings.alpaca_api_key_id or "",
            "APCA-API-SECRET-KEY": settings.alpaca_api_secret_key.get_secret_value(),
        },
        timeout=TIMEOUT_SECONDS,
        transport=transport,
    )


def checked_get(
    http: httpx.Client,
    path: str,
    *,
    error_cls: type[RuntimeError],
    label: str,
    unauthorized_hint: str,
    params: dict | None = None,
) -> httpx.Response:
    """GET with the KUBERA error discipline: wrapped network errors, actionable 401s."""
    try:
        resp = http.get(path, params=params)
    except httpx.HTTPError as e:
        raise error_cls(f"Network error calling {label} {path}: {e!r}") from e
    if resp.status_code == 401:
        raise error_cls(unauthorized_hint)
    if resp.status_code >= 400:
        raise error_cls(f"{label} {path} failed: HTTP {resp.status_code} — {resp.text[:200]}")
    return resp
