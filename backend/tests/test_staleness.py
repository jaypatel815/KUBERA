"""T036b session-aware freshness — the Friday-quote-on-Saturday problem.

Hand cases (all timezone-aware UTC):
- market OPEN, 5 min old      -> live, trustworthy
- market OPEN, 20 min old     -> stale, NOT trustworthy (feed behind = hazard)
- market CLOSED, 2 days old   -> last_session, trustworthy ("most recent real print")
- market CLOSED, 6 days old   -> old, NOT trustworthy (beyond a normal closure)
"""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from test_alpaca import paper_settings

from analysis.staleness import (
    LAST_SESSION_MAX_HOURS,
    MAX_LIVE_AGE_SECONDS,
    classify_freshness,
    next_session_hint,
    wallclock_fallback,
)
from api.tools import ToolContext, registry
from data.alpaca import AlpacaClient
from data.market_data import MarketDataClient

NOW = datetime(2026, 8, 15, 14, 0, 0, tzinfo=timezone.utc)   # a Saturday


def at(**kw):
    return NOW - timedelta(**kw)


# --- pure classification ------------------------------------------------------

def test_live_during_session():
    f = classify_freshness(at(minutes=5), NOW, market_open=True)
    assert f.state == "live" and f.trustworthy
    assert "live" in f.phrase


def test_stale_is_only_possible_while_open():
    f = classify_freshness(at(minutes=20), NOW, market_open=True)
    assert f.state == "stale" and not f.trustworthy
    assert "market is open" in f.phrase and "do not treat it as the current" in f.phrase
    assert MAX_LIVE_AGE_SECONDS == 900.0


def test_friday_quote_on_saturday_is_last_session_not_stale():
    f = classify_freshness(at(days=2), NOW, market_open=False)
    assert f.state == "last_session"
    assert f.trustworthy is True            # the whole point of the ticket
    assert "most recent real print" in f.phrase


def test_boundary_at_last_session_window():
    f_in = classify_freshness(at(hours=LAST_SESSION_MAX_HOURS - 1), NOW,
                              market_open=False)
    f_out = classify_freshness(at(hours=LAST_SESSION_MAX_HOURS + 1), NOW,
                               market_open=False)
    assert f_in.state == "last_session" and f_out.state == "old"
    assert not f_out.trustworthy and "check the data feed" in f_out.phrase


def test_input_validation():
    naive = datetime(2026, 8, 15, 12, 0, 0)
    with pytest.raises(ValueError):
        classify_freshness(naive, NOW, market_open=True)
    with pytest.raises(ValueError):
        classify_freshness(NOW + timedelta(minutes=5), NOW, market_open=True)


def test_wallclock_fallback_says_it_doesnt_know():
    f = wallclock_fallback(at(days=2), NOW)
    assert f.market_open is False
    assert "market state unknown" in f.phrase
    assert f.state == "stale"      # conservative: assumes open, flags the age


def test_next_session_hint():
    assert "opens in" in next_session_hint(NOW + timedelta(hours=14), NOW)
    assert "already be open" in next_session_hint(NOW - timedelta(hours=1), NOW)


# --- tool wiring --------------------------------------------------------------

FRESH_TRADE = {"trade": {"p": 185.0, "s": 1,
                         "t": datetime.now(timezone.utc).isoformat()}}
FRESH_QUOTE = {"quote": {"bp": 184.9, "bs": 1, "ap": 185.1, "as": 1,
                         "t": datetime.now(timezone.utc).isoformat()}}


def clock_json(is_open: bool):
    now = datetime.now(timezone.utc)
    return {"timestamp": now.isoformat(), "is_open": is_open,
            "next_open": (now + timedelta(hours=14)).isoformat(),
            "next_close": (now + timedelta(hours=20)).isoformat()}


def market_fake() -> MarketDataClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/quotes/latest" in request.url.path:
            return httpx.Response(200, json=FRESH_QUOTE)
        return httpx.Response(200, json=FRESH_TRADE)
    return MarketDataClient(settings=paper_settings(),
                            transport=httpx.MockTransport(handler))


def alpaca_fake(is_open: bool) -> AlpacaClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=clock_json(is_open))
    return AlpacaClient(settings=paper_settings(),
                        transport=httpx.MockTransport(handler))


def test_get_latest_uses_broker_clock_when_open():
    with market_fake() as m, alpaca_fake(True) as a:
        out = registry.execute("get_latest", {"symbol": "SPY"},
                               ToolContext(market=m, alpaca=a))
    assert out["freshness"]["state"] == "live"
    assert out["session"]["market_open"] is True
    assert out["session"]["hint"] is None
    assert out["trade"]["price"] == 185.0     # legacy payload preserved


def test_get_latest_closed_market_gets_session_hint():
    with market_fake() as m, alpaca_fake(False) as a:
        out = registry.execute("get_latest", {"symbol": "SPY"},
                               ToolContext(market=m, alpaca=a))
    assert out["freshness"]["state"] == "last_session"
    assert out["freshness"]["trustworthy"] is True
    assert "opens in" in out["session"]["hint"]


def test_get_latest_without_alpaca_falls_back_labeled():
    with market_fake() as m:
        out = registry.execute("get_latest", {"symbol": "SPY"},
                               ToolContext(market=m))
    assert "market state unknown" in out["freshness"]["phrase"]
    assert out["session"]["market_open"] is None
