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

from data._http import build_client, checked_get
from settings import KuberaSettings, get_settings

DATA_BASE_URL = "https://data.alpaca.markets"
FEED = "iex"  # free tier (D006); "sip" requires a paid subscription
SOURCE = f"alpaca-data-{FEED}"

# Stale-data detection (D018): if the exchange event behind a "latest" quote/trade is
# older than this, the payload is flagged stale and KUBERA must not treat it as live.
# Age is exchange_ts -> fetch time; weekends/after-hours will read stale BY DESIGN —
# "this price is from Friday" is exactly what the user should be told.
MAX_DATA_AGE_SECONDS = 900.0  # 15 minutes

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
    age_seconds: float  # asof - exchange_ts; how old the market event actually is
    stale: bool         # age_seconds > MAX_DATA_AGE_SECONDS — never present as live
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
    age_seconds: float
    stale: bool
    source: str = SOURCE


def _age_and_staleness(exchange_ts: datetime, asof: datetime) -> tuple[float, bool]:
    age = (asof - exchange_ts).total_seconds()
    return age, age > MAX_DATA_AGE_SECONDS


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


INTRADAY_TIMEFRAMES = ("1Min", "5Min", "15Min", "30Min", "1Hour")


@dataclass(frozen=True)
class IntradayBar:
    ts: datetime  # bar START time, tz-aware UTC (Alpaca convention)
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class IntradayBars:
    symbol: str
    timeframe: str
    bars: list[IntradayBar]
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
        self._http = build_client(DATA_BASE_URL, s, transport)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "MarketDataClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _get(self, path: str, params: dict | None = None) -> dict:
        return checked_get(
            self._http,
            path,
            params=params,
            error_cls=MarketDataError,
            label="Alpaca data",
            unauthorized_hint=(
                "Alpaca data API rejected the keys (401). Check ALPACA_API_KEY_ID / "
                "ALPACA_API_SECRET_KEY in .env (same keys as the paper account)."
            ),
        ).json()

    def get_latest_trade(self, symbol: str) -> LatestTrade:
        symbol = symbol.upper()
        d = self._get(f"/v2/stocks/{symbol}/trades/latest", params={"feed": FEED})
        t = d["trade"]
        exchange_ts = parse_rfc3339(t["t"])
        asof = datetime.now(timezone.utc)
        age, stale = _age_and_staleness(exchange_ts, asof)
        return LatestTrade(
            symbol=symbol,
            price=float(t["p"]),
            size=float(t["s"]),
            exchange_ts=exchange_ts,
            asof=asof,
            age_seconds=age,
            stale=stale,
        )

    def get_latest_quote(self, symbol: str) -> LatestQuote:
        symbol = symbol.upper()
        d = self._get(f"/v2/stocks/{symbol}/quotes/latest", params={"feed": FEED})
        q = d["quote"]
        exchange_ts = parse_rfc3339(q["t"])
        asof = datetime.now(timezone.utc)
        age, stale = _age_and_staleness(exchange_ts, asof)
        return LatestQuote(
            symbol=symbol,
            bid=float(q["bp"]),
            bid_size=float(q["bs"]),
            ask=float(q["ap"]),
            ask_size=float(q["as"]),
            exchange_ts=exchange_ts,
            asof=asof,
            age_seconds=age,
            stale=stale,
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

    def get_intraday_bars(
        self, symbol: str, timeframe: str = "5Min", days: int = 7
    ) -> IntradayBars:
        """Intraday OHLCV (T052). Timestamps are bar STARTS, tz-aware UTC.
        IEX feed (D006): volumes are a small sample of the consolidated tape —
        valid for the symbol's own relative measures (session VWAP shape, RVOL),
        never for absolute volume claims."""
        if timeframe not in INTRADAY_TIMEFRAMES:
            raise ValueError(
                f"timeframe must be one of {INTRADAY_TIMEFRAMES}, got {timeframe!r}"
            )
        if not 1 <= days <= 30:
            raise ValueError(f"days must be 1..30 for intraday, got {days}")
        symbol = symbol.upper()
        start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        d = self._get(
            f"/v2/stocks/{symbol}/bars",
            params={
                "timeframe": timeframe,
                "start": start,
                "feed": FEED,
                "limit": 10000,
                "adjustment": "split",
            },
        )
        bars = [
            IntradayBar(
                ts=parse_rfc3339(b["t"]),
                open=float(b["o"]),
                high=float(b["h"]),
                low=float(b["l"]),
                close=float(b["c"]),
                volume=float(b["v"]),
            )
            for b in (d.get("bars") or [])
        ]
        return IntradayBars(
            symbol=symbol, timeframe=timeframe, bars=bars,
            asof=datetime.now(timezone.utc),
        )
