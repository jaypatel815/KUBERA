"""Intraday session analysis (T052) — hand-computed VWAP/crossings/RVOL, the ET
midnight boundary, RTH filtering, and the tool/endpoint on a two-session fixture."""

from collections import namedtuple
from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from test_alpaca import paper_settings

from analysis.intraday import build_session_read, group_sessions, session_vwap
from api.main import app
from api.tools import ToolArgumentError, ToolContext, ToolError, registry
from data.market_data import MarketDataClient

client = TestClient(app)

B = namedtuple("B", "ts high low close volume")


def utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


# August 2026 is EDT: 13:30Z == 09:30 ET (RTH open).

def test_session_vwap_hand():
    bars = [
        B(utc(2026, 8, 13, 13, 30), 10.0, 8.0, 9.0, 100.0),    # tp 9
        B(utc(2026, 8, 13, 13, 35), 11.0, 9.0, 10.0, 300.0),   # tp 10
        B(utc(2026, 8, 13, 13, 40), 12.0, 10.0, 11.0, 100.0),  # tp 11
    ]
    # (9*100 + 10*300 + 11*100) / 500 = 5000/500
    assert session_vwap(bars) == pytest.approx(10.0)
    r = build_session_read(bars, volume_feed="test-fixture")
    assert r.session_vwap == pytest.approx(10.0)
    assert r.above_vwap is True and r.last_price == pytest.approx(11.0)
    assert r.vwap_distance_frac == pytest.approx(0.1)
    assert r.cum_volume == pytest.approx(500.0)
    assert r.intraday_rvol is None and r.rvol_sessions_used == 0  # no prior sessions


def test_vwap_crossings_hand():
    def bar(minute, price, v=100.0):
        return B(utc(2026, 8, 13, 13, 30 + minute), price, price, price, v)

    # running VWAP: 10 -> 11 -> 10.333 -> 10.75; closes 10, 12, 9, 12
    # sides: 0 (on vwap), +1 (no flip from 0), -1 (flip 1), +1 (flip 2)
    r = build_session_read(
        [bar(0, 10.0), bar(5, 12.0), bar(10, 9.0), bar(15, 12.0)],
        volume_feed="test-fixture",
    )
    assert r.session_vwap == pytest.approx(10.75)
    assert r.vwap_crossings == 2


def test_et_midnight_boundary_groups_to_prior_session():
    late = B(utc(2026, 8, 11, 0, 30), 10.0, 10.0, 10.0, 1.0)   # 20:30 ET Aug 10
    morning = B(utc(2026, 8, 11, 14, 0), 10.0, 10.0, 10.0, 1.0)  # 10:00 ET Aug 11
    assert list(group_sessions([late, morning])) == ["2026-08-10", "2026-08-11"]
    # RTH filter drops the after-hours bar entirely
    r = build_session_read([late, morning], volume_feed="test-fixture")
    assert r.session_date == "2026-08-11" and r.bars_count == 1


def test_rth_filter_and_extended_hours_opt_in():
    pre = B(utc(2026, 8, 13, 13, 25), 10.0, 10.0, 10.0, 1.0)    # 09:25 ET: pre-open
    rth = B(utc(2026, 8, 13, 13, 30), 10.0, 10.0, 10.0, 1.0)    # 09:30 ET: in
    close_bar = B(utc(2026, 8, 13, 20, 0), 10.0, 10.0, 10.0, 1.0)  # 16:00 ET: out
    r = build_session_read([pre, rth, close_bar], volume_feed="test-fixture")
    assert r.bars_count == 1 and r.last_ts == rth.ts.isoformat()
    r2 = build_session_read([pre, rth, close_bar], volume_feed="test-fixture",
                            rth_only=False)
    assert r2.bars_count == 3
    with pytest.raises(ValueError, match="regular trading hours"):
        build_session_read([pre], volume_feed="test-fixture")


def test_time_of_day_rvol_hand():
    prior = [
        B(utc(2026, 8, 12, 13, 30), 10.0, 10.0, 10.0, 100.0),
        B(utc(2026, 8, 12, 13, 35), 10.0, 10.0, 10.0, 200.0),
        B(utc(2026, 8, 12, 13, 40), 10.0, 10.0, 10.0, 400.0),  # beyond cutoff: excluded
    ]
    today = [
        B(utc(2026, 8, 13, 13, 30), 10.0, 10.0, 10.0, 300.0),
        B(utc(2026, 8, 13, 13, 35), 10.0, 10.0, 10.0, 300.0),
    ]
    r = build_session_read(prior + today, volume_feed="test-fixture")
    # today cum 600 by 09:35 ET vs prior cum-by-09:35 = 300 -> exactly the doctrine
    assert r.intraday_rvol == pytest.approx(2.0)
    assert r.rvol_sessions_used == 1
    assert r.cum_volume == pytest.approx(600.0)


def test_zero_volume_session_degrades_honestly():
    bars = [B(utc(2026, 8, 13, 13, 30 + m), 10.0, 10.0, 10.0, 0.0) for m in (0, 5)]
    r = build_session_read(bars, volume_feed="test-fixture")
    assert r.session_vwap is None and r.above_vwap is None
    assert r.intraday_rvol is None and r.cum_volume == 0.0


def test_validation():
    good = B(utc(2026, 8, 13, 13, 30), 10.0, 9.0, 9.5, 1.0)
    with pytest.raises(ValueError, match="no intraday bars"):
        build_session_read([], volume_feed="x")
    with pytest.raises(ValueError, match="tz-aware"):
        build_session_read([B(datetime(2026, 8, 13, 13, 30), 10, 9, 9.5, 1)],
                           volume_feed="x")
    with pytest.raises(ValueError, match="strictly increasing"):
        build_session_read([good, good], volume_feed="x")
    with pytest.raises(ValueError, match="low"):
        build_session_read([B(utc(2026, 8, 13, 13, 30), 9.0, 10.0, 9.5, 1.0)],
                           volume_feed="x")
    with pytest.raises(ValueError, match="volume_feed"):
        build_session_read([good], volume_feed="  ")
    with pytest.raises(ValueError, match="rvol_sessions"):
        build_session_read([good], volume_feed="x", rvol_sessions=0)


# --- data client --------------------------------------------------------------

def test_client_rejects_bad_intraday_params():
    c = MarketDataClient(settings=paper_settings(),
                         transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    with pytest.raises(ValueError, match="timeframe"):
        c.get_intraday_bars("SPY", timeframe="2Min")
    with pytest.raises(ValueError, match="days"):
        c.get_intraday_bars("SPY", days=31)
    c.close()


# --- tool + endpoint ----------------------------------------------------------

def _bar_json(iso, v):
    return {"t": iso, "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0, "v": v}


INTRADAY_JSON = {
    "symbol": "SPY",
    "next_page_token": None,
    "bars": [
        _bar_json("2026-08-12T13:30:00Z", 1_000_000),
        _bar_json("2026-08-12T13:35:00Z", 1_000_000),
        _bar_json("2026-08-12T13:40:00Z", 1_000_000),
        _bar_json("2026-08-13T13:30:00Z", 2_000_000),
        _bar_json("2026-08-13T13:35:00Z", 2_000_000),
    ],
}


def market_fake(bars_json: dict) -> MarketDataClient:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["timeframe"] in ("1Min", "5Min", "15Min", "30Min", "1Hour")
        return httpx.Response(200, json=bars_json)

    return MarketDataClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def test_get_intraday_tool_executes():
    with market_fake(INTRADAY_JSON) as m:
        out = registry.execute("get_intraday", {"symbol": "SPY"}, ToolContext(market=m))
    r = out["intraday"]
    assert out["timeframe"] == "5Min"
    assert r["session_date"] == "2026-08-13"
    # today 4M by 09:35 ET vs prior day's 2M by the same time
    assert r["intraday_rvol"] == pytest.approx(2.0)
    assert r["session_vwap"] == pytest.approx(100.0)  # tp constant at 100
    assert r["above_vwap"] is False  # close == vwap -> not above
    assert "SIP" in r["volume_note"] and r["volume_feed"] == "alpaca-data-iex"


def test_get_intraday_tool_errors():
    empty = {"symbol": "SPY", "next_page_token": None, "bars": []}
    with market_fake(empty) as m, pytest.raises(ToolError, match="no intraday bars"):
        registry.execute("get_intraday", {"symbol": "SPY"}, ToolContext(market=m))
    with market_fake(INTRADAY_JSON) as m, pytest.raises(ToolArgumentError):
        registry.execute("get_intraday", {"symbol": "SPY", "timeframe": "2Min"},
                         ToolContext(market=m))


def test_intraday_endpoint():
    from api import main as main_module

    def fake_client_dep():
        with market_fake(INTRADAY_JSON) as m:
            yield m

    app.dependency_overrides[main_module.get_market_client] = fake_client_dep
    try:
        r = client.get("/api/intraday/SPY")
    finally:
        app.dependency_overrides.pop(main_module.get_market_client)
    assert r.status_code == 200
    body = r.json()
    assert body["intraday"]["intraday_rvol"] == pytest.approx(2.0)
    assert body["intraday"]["rth_only"] is True
    assert body["asof"]
