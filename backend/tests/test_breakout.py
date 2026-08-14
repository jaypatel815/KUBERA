"""Breakout detector (T053) — the three-part doctrine test, every path hand-walked:
confirmed, failed ($100→$106→$99), unconfirmed (weak volume), pending, both
directions, continuation suppression, and the tool/endpoint."""

import httpx
import pytest
from fastapi.testclient import TestClient
from test_alpaca import paper_settings

from analysis.breakout import detect_breakouts
from api.main import app
from api.tools import ToolContext, ToolError, registry
from data.market_data import MarketDataClient

client = TestClient(app)

MICRO = dict(range_lookback=3, rvol_baseline=3, hold_confirm=2)


def _dates(n: int) -> list[str]:
    return [f"d{i:03d}" for i in range(n)]


def scan(closes, volumes, **kwargs):
    params = {**MICRO, **kwargs}
    return detect_breakouts(closes, closes, closes, volumes, _dates(len(closes)),
                            **params)


def test_the_hundred_to_106_to_99_lesson():
    # the doctrine's canonical fakeout: escape on volume, then straight back INSIDE
    # the range (the floor sits at 95 — 99 is a return, not a downside break)
    closes = [100.0, 100.0, 100.0, 100.0, 106.0, 99.0]
    r = detect_breakouts(closes, [95.0] * 6, closes,
                         [10.0, 10.0, 10.0, 10.0, 30.0, 10.0], _dates(6), **MICRO)
    assert len(r.events) == 1
    e = r.events[0]
    assert e.direction == "up" and e.boundary == pytest.approx(100.0)
    assert e.rvol_at_break == pytest.approx(3.0)  # volume was even confirming...
    assert e.status == "failed"                    # ...and it STILL failed the hold
    assert e.held_bars == 0
    assert "fakeout completed" in e.reason
    assert r.active is False  # a failed break is never active


def test_confirmed_breakout_full_pattern():
    # escape on 3x volume, holds two bars: escape + volume + hold = confirmed
    r = scan([100.0, 100.0, 100.0, 100.0, 105.0, 106.0, 107.0],
             [10.0, 10.0, 10.0, 10.0, 30.0, 10.0, 10.0])
    e = r.latest
    assert e.status == "confirmed" and e.date == "d004"
    assert e.volume_confirmed is True and e.suspected_fakeout is False
    assert e.held_bars == 2
    assert r.active is True  # last close 107 still beyond boundary 100


def test_weak_volume_hold_is_unconfirmed_and_suspected():
    r = scan([100.0, 100.0, 100.0, 100.0, 105.0, 106.0, 107.0],
             [30.0, 30.0, 30.0, 30.0, 15.0, 30.0, 30.0])
    e = r.latest
    assert e.rvol_at_break == pytest.approx(0.5)
    assert e.suspected_fakeout is True and e.volume_confirmed is False
    assert e.status == "unconfirmed"  # held the range but volume never blessed it
    assert "stay suspicious" in e.reason


def test_break_on_last_bar_is_pending():
    r = scan([100.0, 100.0, 100.0, 100.0, 105.0],
             [10.0, 10.0, 10.0, 10.0, 30.0])
    assert r.latest.status == "pending" and r.latest.held_bars == 0
    assert r.active is True


def test_two_events_up_failed_then_down_confirmed():
    closes = [100.0, 100.0, 100.0, 100.0, 105.0, 106.0,
              100.0, 100.0, 100.0, 93.0, 92.0, 91.0]
    volumes = [10.0, 10.0, 10.0, 10.0, 30.0, 10.0,
               10.0, 10.0, 10.0, 30.0, 10.0, 10.0]
    r = scan(closes, volumes)
    # continuation bars (106 after 105; 92/91 after 93) never start new events
    assert [(e.direction, e.status) for e in r.events] == [
        ("up", "failed"), ("down", "confirmed"),
    ]
    down = r.events[1]
    assert down.boundary == pytest.approx(100.0) and down.date == "d009"
    assert down.held_bars == 2
    assert r.active is True  # last close 91 still below 100


def test_validation():
    flat = [100.0] * 6
    vols = [10.0] * 6
    with pytest.raises(ValueError, match="equal length"):
        detect_breakouts(flat[:5], flat, flat, vols, _dates(6), **MICRO)
    with pytest.raises(ValueError, match="at least 4"):
        scan([100.0, 100.0, 100.0], [10.0] * 3)
    with pytest.raises(ValueError, match="volume"):
        scan(flat, [10.0, 10.0, -1.0, 10.0, 10.0, 10.0])
    with pytest.raises(ValueError, match=">= 1"):
        scan(flat, vols, hold_confirm=0)


# --- tool + endpoint (defaults: L=20, B=20, hold=2) ---------------------------

CONFIRMED_BARS_JSON = {
    "symbol": "SPY",
    "next_page_token": None,
    "bars": [
        {"t": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T04:00:00Z",
         "o": 100.0, "h": 100.5, "l": 99.5, "c": 100.0, "v": 1_000_000}
        for i in range(20)
    ] + [
        {"t": "2026-01-21T04:00:00Z", "o": 101.0, "h": 105.5, "l": 100.5,
         "c": 105.0, "v": 3_000_000},
        {"t": "2026-01-22T04:00:00Z", "o": 105.0, "h": 106.5, "l": 105.5,
         "c": 106.0, "v": 1_500_000},
        {"t": "2026-01-23T04:00:00Z", "o": 106.0, "h": 107.5, "l": 106.5,
         "c": 107.0, "v": 1_500_000},
    ],
}


def market_fake(bars_json: dict) -> MarketDataClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=bars_json)

    return MarketDataClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def test_get_breakouts_tool_executes():
    with market_fake(CONFIRMED_BARS_JSON) as m:
        out = registry.execute("get_breakouts", {"symbol": "SPY"}, ToolContext(market=m))
    b = out["breakouts"]
    assert len(b["events"]) == 1
    e = b["events"][0]
    assert e["status"] == "confirmed" and e["direction"] == "up"
    assert e["boundary"] == pytest.approx(100.5)
    assert e["rvol_at_break"] == pytest.approx(3.0)
    assert b["active"] is True
    assert out["volume_feed"] == "alpaca-data-iex"  # D006 label rides along
    assert out["asof"]


def test_get_breakouts_tool_rejects_thin_history():
    thin = {"symbol": "SPY", "next_page_token": None,
            "bars": CONFIRMED_BARS_JSON["bars"][:5]}
    with market_fake(thin) as m, pytest.raises(ToolError, match="21"):
        registry.execute("get_breakouts", {"symbol": "SPY"}, ToolContext(market=m))


def test_breakouts_endpoint():
    from api import main as main_module

    def fake_client_dep():
        with market_fake(CONFIRMED_BARS_JSON) as m:
            yield m

    app.dependency_overrides[main_module.get_market_client] = fake_client_dep
    try:
        r = client.get("/api/breakouts/SPY")
    finally:
        app.dependency_overrides.pop(main_module.get_market_client)
    assert r.status_code == 200
    body = r.json()
    assert body["breakouts"]["latest"]["status"] == "confirmed"
    assert body["breakouts"]["as_of_date"] == "2026-01-23"
    assert body["asof"]
