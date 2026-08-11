"""Alpaca Market Data client (T012) — US equities via the free IEX feed.

Every payload carries TWO timestamps, per AGENTS.md ("no stale data presented as current"):
- `exchange_ts` — when the market event actually happened (from the exchange feed)
- `asof`        — when KUBERA fetched it

The free IEX feed covers ~2-3% of market volume in real time; quotes can differ slightly
from consolidated SIP data (paid). Fine for v1 per D006; upgrade path is a `feed` switch.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

from settings import KuberaSettings, get_settings

DATA_BASE_URL = "https://data.alpaca.markets"
FEED = "iex"  # free tier (D006); "sip" requires a paid subscription
SOURCE = f"alpaca-data-{FEED}"

_FRACTION_RE = re.compile(r"\.(\d+)")


class MarketDataError(RuntimeError):
    """Market data API returned an error; message includes status code and hint."""


def parse_rfc3339(ts: str) -> datetime:
    """Parse Alpaca RFC3339 timestamps on Python 3.10+.

    Alpaca emits variable-precision fractions (".5", ".123456789"); 3.10's fromisoformat
    accepts only exactly 3 or 6 digits, so normalize the fraction to microseconds.
    """
    ts = _FRACTION_RE.sub(lambda m: "." + (m.group(1) + "000000")[:6], ts.strip())
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


@dataclass(frozen=True)
class LatestTrade:
    symbol: str
    price: float
    size: float
    exchange_ts: datetime
    asof: datetime
    source: str = SOURCE


@dataclass(frozen=True)
class LatestQuote:
    symbol: str
    bid: float
    bid_size: float
    ask: float
    ask_size: float
    exchange_ts: datetime
    asof: datetime
    source: str = SOURCE


@dataclass(frozen=True)
class DailyBar:
    date: str  # YYYY-MM-DD (exchange session date)
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class DailyBars:
    symbol: str
    bars: list[DailyBar]
    asof: datetime
    source: str = SOURCE


class MarketDataClient:
    """Data-only client (no order capability exists on this API surface at all)."""

    def __init__(
        self,
        settings: KuberaSettings | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        s = (settings or get_settings()).require_alpaca()
        assert s.alpaca_api_secret_key is not None  # guaranteed by require_alpaca()
        self._http = httpx.Client(
            base_url=DATA_BASE_URL,
            headers={
                "APCA-API-KEY-ID": s.alpaca_api_key_id or "",
                "APCA-API-SECRET-KEY": s.alpaca_api_secret_key.get_secret_value(),
            },
            timeout=15.0,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "MarketDataClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _get(self, path: str, params: dict | None = None) -> dict:
        try:
            resp = self._http.get(path, params=params)
        except httpx.HTTPError as e:
            raise MarketDataError(f"Network error calling Alpaca data {path}: {e!r}") from e
        if resp.status_code == 401:
            raise MarketDataError(
                "Alpaca data API rejected the keys (401). Check ALPACA_API_KEY_ID / "
                "ALPACA_API_SECRET_KEY in .env (same keys as the paper account)."
            )
        if resp.status_code >= 400:
            raise MarketDataError(
                f"Alpaca data {path} failed: HTTP {resp.status_code} — {resp.text[:200]}"
            )
        return resp.json()

    def get_latest_trade(self, symbol: str) -> LatestTrade:
        symbol = symbol.upper()
        d = self._get(f"/v2/stocks/{symbol}/trades/latest", params={"feed": FEED})
        t = d["trade"]
        return LatestTrade(
            symbol=symbol,
            price=float(t["p"]),
            size=float(t["s"]),
            exchange_ts=parse_rfc3339(t["t"]),
            asof=datetime.now(timezone.utc),
        )

    def get_latest_quote(self, symbol: str) -> LatestQuote:
        symbol = symbol.upper()
        d = self._get(f"/v2/stocks/{symbol}/quotes/latest", params={"feed": FEED})
        q = d["quote"]
        return LatestQuote(
            symbol=symbol,
            bid=float(q["bp"]),
            bid_size=float(q["bs"]),
            ask=float(q["ap"]),
            ask_size=float(q["as"]),
            exchange_ts=parse_rfc3339(q["t"]),
            asof=datetime.now(timezone.utc),
        )

    def get_daily_bars(self, symbol: str, days: int = 30) -> DailyBars:
        """Daily OHLCV for the last `days` calendar days (single page; 10k bar limit)."""
        if not 1 <= days <= 3650:
            raise ValueError(f"days must be 1..3650, got {days}")
        symbol = symbol.upper()
        start = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
        d = self._get(
            f"/v2/stocks/{symbol}/bars",
            params={
                "timeframe": "1Day",
                "start": start,
                "feed": FEED,
                "limit": 10000,
                "adjustment": "split",
            },
        )
        bars = [
            DailyBar(
                date=parse_rfc3339(b["t"]).date().isoformat(),
                open=float(b["o"]),
                high=float(b["h"]),
                low=float(b["l"]),
                close=float(b["c"]),
                volume=float(b["v"]),
            )
            for b in (d.get("bars") or [])
        ]
        return DailyBars(symbol=symbol, bars=bars, asof=datetime.now(timezone.utc))
