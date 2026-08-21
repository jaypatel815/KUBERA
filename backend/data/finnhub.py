"""T121 — Finnhub free-tier client (D030/D037). OWNER-PROBED 2026-08-20:
quote OK · company-news OK (244 articles/31d) · earnings surprises OK
(4 quarters actual-vs-estimate — THE PRIZE) · stock/metric OK (133) ·
news-sentiment PAYWALLED (403). This client speaks exactly the probed
endpoints and nothing else; sentiment is deliberately absent until a paid
tier measures differently (D034).

Why the surprises matter: T083's base rates split reactions by beat/miss,
but the owner's FMP tier paywalls past estimates — so "unknown" dominates.
Finnhub's actual-vs-estimate history fills exactly that hole. The catch,
handled fail-closed downstream: Finnhub rows carry the fiscal PERIOD END,
not the report date — matching a surprise to a stored report date is the
enrichment layer's job (earnings_store.enrich_from_surprises) under an
unambiguous-match rule, never a guess (T102).

Etiquette: free tier allows 60 calls/min; this client makes single calls,
no retry loops (a 429 is NAMED and surrendered to the caller).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

import httpx

from settings import ConfigError, KuberaSettings, get_settings


class FinnhubError(RuntimeError):
    pass


@dataclass(frozen=True)
class EarningsSurprise:
    symbol: str
    period_end: date              # FISCAL period end — NOT the report date
    eps_actual: float | None
    eps_estimated: float | None


@dataclass(frozen=True)
class SurprisesResult:
    symbol: str
    rows: list[EarningsSurprise] = field(default_factory=list)
    unparsed: int = 0             # rows missing a parseable period — reported
    asof: str = ""
    source: str = "finnhub-free"


@dataclass(frozen=True)
class NewsItem:
    headline: str
    published_utc: datetime | None
    news_source: str
    url: str


@dataclass(frozen=True)
class NewsResult:
    symbol: str
    items: list[NewsItem] = field(default_factory=list)
    total_returned: int = 0       # before the cap — the cap is visible
    asof: str = ""
    source: str = "finnhub-free"


NEWS_CAP = 50                     # newest N; 244/31d observed — cap the payload


class FinnhubClient:
    """Read-only, three probed endpoints, transport-injectable for tests."""

    def __init__(self, settings: KuberaSettings | None = None,
                 transport: httpx.BaseTransport | None = None):
        s = settings or get_settings()
        if not s.finnhub_api_key or not s.finnhub_api_key.get_secret_value().strip():
            raise ConfigError(
                "FINNHUB_API_KEY is not set — free key at https://finnhub.io "
                "(the owner's probe verified the tier answers).")
        self._client = httpx.Client(
            base_url=s.finnhub_base_url, timeout=30.0, transport=transport,
            params={"token": s.finnhub_api_key.get_secret_value().strip()},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "FinnhubClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _get(self, path: str, params: dict, what: str):
        try:
            r = self._client.get(path, params=params)
        except httpx.HTTPError as e:
            raise FinnhubError(
                f"network error calling Finnhub {what}: "
                f"{type(e).__name__}") from e
        if r.status_code == 401:
            raise FinnhubError(f"Finnhub refused {what} (HTTP 401) — "
                               "check FINNHUB_API_KEY")
        if r.status_code == 403:
            raise FinnhubError(f"Finnhub {what} is PAYWALLED (HTTP 403) — "
                               "not on the free tier (D034)")
        if r.status_code == 429:
            raise FinnhubError("Finnhub rate limit (HTTP 429) — 60/min on "
                               "the free tier; do not retry in a loop")
        if r.status_code >= 400:
            raise FinnhubError(f"Finnhub {what} failed: HTTP {r.status_code}")
        try:
            return r.json()
        except ValueError as e:
            raise FinnhubError(f"Finnhub {what} returned non-JSON") from e

    def quote(self, symbol: str) -> dict:
        """T157i — /quote for one symbol (works for indices like ^DJI/^GSPC on
        keys that carry them). Finnhub answers c=0 for symbols it will not
        serve — that is a REFUSAL, raised by name, never rendered as a price
        of zero."""
        data = self._get("/quote", {"symbol": symbol}, f"quote({symbol})")
        c = data.get("c")
        if not c:
            raise FinnhubError(
                f"Finnhub has no quote for '{symbol}' on this key (c=0) — "
                "index quotes may not be included in the free tier")
        return {
            "price": float(c),
            "change": float(data.get("d") or 0.0),
            "change_pct": float(data.get("dp") or 0.0),
            "prev_close": (float(data["pc"]) if data.get("pc") else None),
        }

    def earnings_surprises(self, symbol: str) -> SurprisesResult:
        """Probed shape: a LIST of {actual, estimate, period, symbol, ...};
        the free tier returned 4 quarters. Fail-closed: a row without a
        parseable period is COUNTED in unparsed, never guessed (T102)."""
        symbol = symbol.upper()
        data = self._get("/stock/earnings", {"symbol": symbol},
                         "earnings surprises")
        if not isinstance(data, list):
            raise FinnhubError("earnings surprises shape changed (not a "
                               "list) — refusing to guess")
        rows: list[EarningsSurprise] = []
        unparsed = 0
        for raw in data:
            if not isinstance(raw, dict):
                unparsed += 1
                continue
            try:
                period = date.fromisoformat(str(raw.get("period"))[:10])
            except (TypeError, ValueError):
                unparsed += 1
                continue

            def _num(v: object) -> float | None:
                try:
                    return float(v) if v is not None else None
                except (TypeError, ValueError):
                    return None

            rows.append(EarningsSurprise(
                symbol=symbol, period_end=period,
                eps_actual=_num(raw.get("actual")),
                eps_estimated=_num(raw.get("estimate"))))
        rows.sort(key=lambda r: r.period_end)
        return SurprisesResult(symbol=symbol, rows=rows, unparsed=unparsed,
                               asof=datetime.now(timezone.utc).isoformat())

    def company_news(self, symbol: str, days: int = 31) -> NewsResult:
        """Probed shape: a LIST of articles with headline/datetime(unix)/
        source/url. Newest NEWS_CAP kept; the pre-cap count is visible."""
        symbol = symbol.upper()
        today = datetime.now(timezone.utc).date()
        data = self._get(
            "/company-news",
            {"symbol": symbol,
             "from": (today - timedelta(days=days)).isoformat(),
             "to": today.isoformat()},
            "company news")
        if not isinstance(data, list):
            raise FinnhubError("company news shape changed (not a list) — "
                               "refusing to guess")
        items: list[NewsItem] = []
        for raw in data:
            if not isinstance(raw, dict) or not raw.get("headline"):
                continue
            ts = None
            try:
                ts = datetime.fromtimestamp(int(raw.get("datetime") or 0),
                                            tz=timezone.utc)
            except (TypeError, ValueError, OSError):
                ts = None
            items.append(NewsItem(
                headline=str(raw["headline"])[:300],
                published_utc=ts,
                news_source=str(raw.get("source") or "?")[:60],
                url=str(raw.get("url") or "")[:500]))
        _floor = datetime.min.replace(tzinfo=timezone.utc)
        items.sort(key=lambda i: i.published_utc or _floor, reverse=True)
        return NewsResult(symbol=symbol, items=items[:NEWS_CAP],
                          total_returned=len(items),
                          asof=datetime.now(timezone.utc).isoformat())
