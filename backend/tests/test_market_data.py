"""Unit tests for the market data client — no network; httpx.MockTransport only."""

import httpx
import pytest
from test_alpaca import paper_settings

from data.market_data import (
    DATA_BASE_URL,
    MarketDataClient,
    MarketDataError,
    parse_rfc3339,
)

TRADE_JSON = {
    "symbol": "AAPL",
    "trade": {"t": "2026-08-11T15:59:59.123456789Z", "p": 229.83, "s": 100, "x": "V"},
}

QUOTE_JSON = {
    "symbol": "AAPL",
    "quote": {
        "t": "2026-08-11T15:59:58.5Z",
        "bp": 229.80,
        "bs": 5,
        "ap": 229.85,
        "as": 3,
    },
}

BARS_JSON = {
    "symbol": "AAPL",
    "next_page_token": None,
    "bars": [
        {"t": "2026-08-08T04:00:00Z", "o": 225.0, "h": 230.1, "l": 224.5, "c": 229.9,
         "v": 51000000},
        {"t": "2026-08-11T04:00:00Z", "o": 229.0, "h": 231.0, "l": 228.2, "c": 230.4,
         "v": 48000000},
    ],
}


def make_client(handler) -> MarketDataClient:
    return MarketDataClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def test_parse_rfc3339_handles_nanoseconds_and_z():
    dt = parse_rfc3339("2026-08-11T15:59:59.123456789Z")
    assert dt.tzinfo is not None
    assert dt.microsecond == 123456


def test_parse_rfc3339_handles_short_fractions_and_none():
    assert parse_rfc3339("2026-08-11T15:59:58.5Z").microsecond == 500000
    assert parse_rfc3339("2026-08-11T15:59:58Z").microsecond == 0


def test_latest_trade_dual_timestamps():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/stocks/AAPL/trades/latest"
        assert request.url.params["feed"] == "iex"
        assert str(request.url).startswith(DATA_BASE_URL)
        return httpx.Response(200, json=TRADE_JSON)

    with make_client(handler) as c:
        trade = c.get_latest_trade("aapl")  # lowercase in, canonical out
    assert trade.symbol == "AAPL"
    assert trade.price == pytest.approx(229.83)
    assert trade.exchange_ts.tzinfo is not None
    assert trade.asof.tzinfo is not None
    assert trade.asof >= trade.exchange_ts.replace(year=trade.asof.year - 1)  # sanity
    assert trade.source == "alpaca-data-iex"


def test_latest_quote_parses_bid_ask():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=QUOTE_JSON)

    with make_client(handler) as c:
        q = c.get_latest_quote("AAPL")
    assert q.bid == pytest.approx(229.80)
    assert q.ask == pytest.approx(229.85)
    assert q.ask_size == 3
    assert q.exchange_ts.tzinfo is not None


def test_daily_bars_parses_and_dates():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["timeframe"] == "1Day"
        assert request.url.params["adjustment"] == "split"
        return httpx.Response(200, json=BARS_JSON)

    with make_client(handler) as c:
        series = c.get_daily_bars("AAPL", days=5)
    assert len(series.bars) == 2
    assert series.bars[0].date == "2026-08-08"
    assert series.bars[-1].close == pytest.approx(230.4)
    assert series.asof.tzinfo is not None


def test_daily_bars_rejects_bad_days():
    with make_client(lambda r: httpx.Response(200, json=BARS_JSON)) as c:
        with pytest.raises(ValueError):
            c.get_daily_bars("AAPL", days=0)


def test_401_actionable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "unauthorized"})

    with make_client(handler) as c, pytest.raises(MarketDataError) as exc:
        c.get_latest_trade("AAPL")
    assert "401" in str(exc.value)
