"""Timeframe confluence (T075) — every adjustment rule hand-computed, plus the
tool routing three timeframes and the endpoint."""

import httpx
import pytest
from fastapi.testclient import TestClient
from test_alpaca import paper_settings

from analysis.confluence import assess_confluence
from api.main import app
from api.tools import ToolContext, ToolError, registry
from data.market_data import MarketDataClient

client = TestClient(app)


# --- adjustment rules, hand-computed ------------------------------------------

def test_full_agreement_caps_at_090():
    r = assess_confluence("trending_up", 0.8, intraday_regime="trending_up",
                          intraday_confidence=0.65, above_vwap=True,
                          vwap_crossings=1)
    assert r.regime_agreement == "agree" and r.vwap_alignment == "aligned"
    # 0.8 + 0.05 + 0.05 = 0.9 — exactly the cap; never beyond
    assert r.adjusted_confidence == pytest.approx(0.9)
    assert len(r.adjustments) == 2 and not r.churn


def test_full_conflict_subtracts_everything():
    r = assess_confluence("trending_up", 0.8, intraday_regime="trending_down",
                          above_vwap=False, vwap_crossings=5)
    assert r.regime_agreement == "conflict" and r.vwap_alignment == "conflict"
    assert r.churn is True
    # 0.8 - 0.10 - 0.05 - 0.05 = 0.60
    assert r.adjusted_confidence == pytest.approx(0.60)
    assert len(r.adjustments) == 3


def test_neutral_daily_direction_means_no_adjustments():
    r = assess_confluence("range_bound", 0.65, intraday_regime="trending_up",
                          above_vwap=True, vwap_crossings=2)
    assert r.regime_agreement == "neutral" and r.vwap_alignment == "neutral"
    assert r.adjusted_confidence == pytest.approx(0.65)
    assert r.adjustments == []


def test_downtrend_below_vwap_is_aligned():
    r = assess_confluence("trending_down", 0.65, intraday_regime="trending_down",
                          above_vwap=False, vwap_crossings=0)
    assert r.vwap_alignment == "aligned"
    assert r.adjusted_confidence == pytest.approx(0.75)


def test_missing_views_are_neutral_and_floor_holds():
    r = assess_confluence("trending_up", 0.35)
    assert r.adjusted_confidence == pytest.approx(0.35) and r.adjustments == []
    low = assess_confluence("trending_up", 0.1, intraday_regime="trending_down",
                            above_vwap=False, vwap_crossings=9)
    assert low.adjusted_confidence == pytest.approx(0.05)  # floored, never zero


def test_validation():
    with pytest.raises(ValueError, match="daily_regime"):
        assess_confluence("sideways", 0.5)
    with pytest.raises(ValueError, match="intraday_regime"):
        assess_confluence("trending_up", 0.5, intraday_regime="chop")
    with pytest.raises(ValueError, match="confidence"):
        assess_confluence("trending_up", 1.5)


# --- tool + endpoint: three timeframes routed by the fake ---------------------

def _sawtooth_closes(n):
    closes = [100.0]
    factors = [1.02, 1.02, 1.02, 1.02, 0.97]
    for i in range(n - 1):
        closes.append(closes[-1] * factors[i % 5])
    return closes


def _daily_json():
    return {"symbol": "SPY", "next_page_token": None, "bars": [
        {"t": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T04:00:00Z",
         "o": c, "h": c * 1.002, "l": c * 0.998, "c": c, "v": 1_000_000}
        for i, c in enumerate(_sawtooth_closes(100))
    ]}


def _hourly_json():
    # same rising sawtooth on hourly stamps -> intraday regime agrees
    return {"symbol": "SPY", "next_page_token": None, "bars": [
        {"t": f"2026-08-{3 + i // 7:02d}T{13 + i % 7:02d}:30:00Z",
         "o": c, "h": c * 1.002, "l": c * 0.998, "c": c, "v": 1_000_000}
        for i, c in enumerate(_sawtooth_closes(50))
    ]}


def _five_min_json():
    # prior session + today's two bars closing above the running VWAP
    def bar(iso, c):
        return {"t": iso, "o": c, "h": c + 1.0, "l": c - 1.0, "c": c, "v": 1_000_000}
    return {"symbol": "SPY", "next_page_token": None, "bars": [
        bar("2026-08-12T13:30:00Z", 100.0), bar("2026-08-12T13:35:00Z", 100.0),
        bar("2026-08-13T13:30:00Z", 100.0), bar("2026-08-13T13:35:00Z", 102.0),
    ]}


def routing_handler(request: httpx.Request) -> httpx.Response:
    tf = request.url.params["timeframe"]
    if tf == "1Day":
        return httpx.Response(200, json=_daily_json())
    if tf == "1Hour":
        return httpx.Response(200, json=_hourly_json())
    return httpx.Response(200, json=_five_min_json())


def market_fake(handler=routing_handler) -> MarketDataClient:
    return MarketDataClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def test_get_confluence_tool_full_stack():
    with market_fake() as m:
        out = registry.execute("get_confluence", {"symbol": "SPY"}, ToolContext(market=m))
    c = out["confluence"]
    assert c["daily_regime"] == "trending_up"
    assert c["intraday_regime"] == "trending_up"
    assert c["regime_agreement"] == "agree"
    assert c["above_vwap"] is True and c["vwap_alignment"] == "aligned"
    assert c["adjusted_confidence"] > c["daily_confidence"]
    assert c["adjusted_confidence"] <= 0.9
    assert out["gaps"] == {"intraday": None, "session": None}
    assert "SIP" in c["note"]  # D006 honesty travels with the reading


def test_confluence_degrades_when_intraday_is_thin():
    def handler(request: httpx.Request) -> httpx.Response:
        tf = request.url.params["timeframe"]
        if tf == "1Day":
            return httpx.Response(200, json=_daily_json())
        return httpx.Response(200, json={"symbol": "SPY", "next_page_token": None,
                                         "bars": []})

    with market_fake(handler) as m:
        out = registry.execute("get_confluence", {"symbol": "SPY"}, ToolContext(market=m))
    c = out["confluence"]
    assert c["intraday_regime"] is None and c["regime_agreement"] == "neutral"
    assert c["adjusted_confidence"] == pytest.approx(c["daily_confidence"])
    assert out["gaps"]["intraday"] is not None
    assert out["gaps"]["session"] is not None


def test_confluence_tool_rejects_thin_daily():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"symbol": "SPY", "next_page_token": None,
                                         "bars": _daily_json()["bars"][:5]})

    with market_fake(handler) as m, pytest.raises(ToolError, match="21"):
        registry.execute("get_confluence", {"symbol": "SPY"}, ToolContext(market=m))


def test_confluence_endpoint():
    from api import main as main_module

    def fake_market():
        with market_fake() as m:
            yield m

    app.dependency_overrides[main_module.get_market_client] = fake_market
    try:
        r = client.get("/api/confluence/SPY")
    finally:
        app.dependency_overrides.pop(main_module.get_market_client)
    assert r.status_code == 200
    assert r.json()["confluence"]["regime_agreement"] == "agree"
