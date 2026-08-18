"""T023 v1 — FMP earnings calendar (D030). FREE tier, probe-verified.

What the owner's tier actually answers (scripts/fmp_check.py, 2026-08-17, his
machine): /stable/earnings-calendar OK (77 rows), statements OK (5 annual
periods), news and transcripts PAYWALLED, the /api/v3 calendar PAYWALLED. So
this client speaks ONLY the /stable family, and news stays with Alpaca (D022).

Parsing is fail-closed per the T102 rule: a row missing its symbol or date is
REPORTED in `unparsed`, never guessed and never silently dropped. Estimate
fields are optional pass-throughs — an earnings DATE is a fact, an EPS
estimate is someone's opinion, and the payload keeps that distinction.

Free tier budget: 250 requests/day. One calendar call covers a date window for
ALL symbols, so normal use is a handful of calls — but the client never
retries on 429; it surfaces the limit with the reset advice instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import httpx

from settings import ConfigError, KuberaSettings, get_settings


class FmpError(RuntimeError):
    pass


@dataclass(frozen=True)
class EarningsEvent:
    symbol: str
    date: date
    time_hint: str | None          # "bmo" (before open) / "amc" (after close) / raw
    eps_estimated: float | None
    revenue_estimated: float | None
    fiscal_ending: str | None


@dataclass(frozen=True)
class EarningsCalendar:
    events: list[EarningsEvent] = field(default_factory=list)
    unparsed: list[dict] = field(default_factory=list)
    from_date: str = ""
    to_date: str = ""
    asof: str = ""
    source: str = "fmp-free"


def _parse_event(row: Any) -> EarningsEvent | dict:
    """One calendar row -> EarningsEvent, or a reported-unparsed dict."""
    if not isinstance(row, dict):
        return {"why": "row is not an object", "row": str(row)[:80]}
    sym = str(row.get("symbol", "")).strip().upper()
    raw_date = row.get("date") or row.get("earningsDate")
    if not sym or not raw_date:
        return {"why": "missing symbol or date — refusing to guess",
                "row": str({k: row.get(k) for k in ("symbol", "date")})[:80]}
    try:
        d = date.fromisoformat(str(raw_date)[:10])
    except ValueError:
        return {"why": f"unparseable date {str(raw_date)[:20]!r}", "row": sym}

    def num(*keys: str) -> float | None:
        for k in keys:
            v = row.get(k)
            if isinstance(v, (int, float)):
                return float(v)
        return None

    time_hint = row.get("time") or row.get("timing")
    return EarningsEvent(
        symbol=sym,
        date=d,
        time_hint=str(time_hint).lower() if time_hint else None,
        eps_estimated=num("epsEstimated", "epsEstimate"),
        revenue_estimated=num("revenueEstimated", "revenueEstimate"),
        fiscal_ending=(str(row["fiscalDateEnding"])
                       if row.get("fiscalDateEnding") else None),
    )


class FmpClient:
    """Read-only, /stable family only, transport-injectable for tests."""

    def __init__(self, settings: KuberaSettings | None = None,
                 transport: httpx.BaseTransport | None = None):
        s = settings or get_settings()
        if not s.fmp_api_key or not s.fmp_api_key.get_secret_value():
            raise ConfigError(
                "FMP_API_KEY is not set. The free key from "
                "https://site.financialmodelingprep.com unlocks the earnings "
                "calendar (probe-verified); put it in .env as FMP_API_KEY."
            )
        self._key = s.fmp_api_key.get_secret_value()
        self._client = httpx.Client(base_url=s.fmp_base_url, timeout=30.0,
                                    transport=transport)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "FmpClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _get(self, path: str, params: dict) -> Any:
        r = self._client.get(path, params={**params, "apikey": self._key})
        if r.status_code == 429:
            raise FmpError(
                "FMP rate limit hit (free tier: 250 requests/day, resets daily). "
                "Do not retry in a loop — wait for the reset."
            )
        if r.status_code in (401, 402, 403):
            raise FmpError(
                f"FMP refused {path} (HTTP {r.status_code}) — key invalid or the "
                "endpoint is paywalled on this tier. scripts/fmp_check.py shows "
                "what the tier answers."
            )
        if r.status_code >= 400:
            raise FmpError(f"FMP {path} failed: HTTP {r.status_code}")
        try:
            return r.json()
        except ValueError as e:
            raise FmpError(f"FMP {path} returned non-JSON") from e

    def _get_list(self, path: str, params: dict, what: str) -> list:
        data = self._get(path, params)
        if not isinstance(data, list):
            raise FmpError(f"{what} returned a non-list — the endpoint shape "
                           "changed; refusing to guess at it")
        return data

    def cash_flow_statement(self, symbol: str, limit: int = 5) -> list:
        """Annual cash-flow rows, newest first. Probe-verified on the free
        tier (fmp_check 2026-08-17: 5 periods)."""
        return self._get_list("/stable/cash-flow-statement",
                              {"symbol": symbol.upper(), "limit": limit},
                              "cash-flow-statement")

    def balance_sheet(self, symbol: str, limit: int = 1) -> list:
        """Annual balance-sheet rows, newest first. NOT yet probe-verified on
        the owner's tier (T023b added the fmp_check row) — a paywall surfaces
        as the named 402/403 FmpError, and callers degrade with a note."""
        return self._get_list("/stable/balance-sheet-statement",
                              {"symbol": symbol.upper(), "limit": limit},
                              "balance-sheet-statement")

    def profile_market_cap(self, symbol: str) -> float | None:
        """Market cap from /stable/profile (probe-verified). None when the
        payload lacks a usable number — reported by the caller, never guessed."""
        data = self._get_list("/stable/profile", {"symbol": symbol.upper()},
                              "profile")
        if not data or not isinstance(data[0], dict):
            return None
        v = data[0].get("marketCap") or data[0].get("mktCap")
        return float(v) if isinstance(v, (int, float)) and v > 0 else None

    def earnings_calendar(self, from_date: date, to_date: date) -> EarningsCalendar:
        """All symbols' earnings dates in [from_date, to_date] — one request."""
        if to_date < from_date:
            raise ValueError("to_date must be >= from_date")
        data = self._get("/stable/earnings-calendar",
                         {"from": from_date.isoformat(), "to": to_date.isoformat()})
        if not isinstance(data, list):
            raise FmpError(
                "earnings-calendar returned a non-list — the endpoint shape "
                "changed; refusing to guess at it"
            )
        events: list[EarningsEvent] = []
        unparsed: list[dict] = []
        for row in data:
            out = _parse_event(row)
            if isinstance(out, EarningsEvent):
                events.append(out)
            else:
                unparsed.append(out)
        events.sort(key=lambda e: (e.date, e.symbol))
        return EarningsCalendar(
            events=events,
            unparsed=unparsed,
            from_date=from_date.isoformat(),
            to_date=to_date.isoformat(),
            asof=datetime.now().astimezone().isoformat(),
        )
