"""get_symbol_briefing tool + /api/briefing endpoint — no network."""

import httpx
import pytest
from fastapi.testclient import TestClient
from test_alpaca import ACCOUNT_JSON, POSITIONS_JSON, paper_settings

from api.main import app, get_alpaca_client, get_market_client
from api.tools import ToolContext, registry
from data.alpaca import AlpacaClient
from data.market_data import MarketDataClient

client = TestClient(app)

# 60 rising daily bars for AAPL: closes 100..159
BARS_JSON = {
    "symbol": "AAPL",
    "next_page_token": None,
    "bars": [
        {"t": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T04:00:00Z",
         "o": 1, "h": 1, "l": 1, "c": float(100 + i), "v": 1}
        for i in range(60)
    ],
}


def market_fake() -> MarketDataClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BARS_JSON)

    return MarketDataClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def alpaca_fake() -> AlpacaClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/v2/account" in request.url.path:
            return httpx.Response(200, json=ACCOUNT_JSON)
        return httpx.Response(200, json=POSITIONS_JSON)

    return AlpacaClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def test_tool_without_alpaca_context_omits_position():
    with market_fake() as m:
        out = registry.execute("get_symbol_briefing", {"symbol": "AAPL"}, ToolContext(market=m))
    b = out["briefing"]
    assert b["symbol"] == "AAPL"
    assert b["last_close"] == 159.0
    assert b["bars_count"] == 60
    assert b["return_20d"] == pytest.approx(159 / 139 - 1)
    assert b["return_60d"] is None  # needs 61 bars
    assert b["sma_50"] == pytest.approx(sum(range(110, 160)) / 50)
    assert b["position"] is None
    assert out["asof"] and out["source"].startswith("alpaca-data")


def test_tool_with_alpaca_context_includes_held_position():
    with market_fake() as m, alpaca_fake() as a:
        out = registry.execute(
            "get_symbol_briefing", {"symbol": "aapl"}, ToolContext(market=m, alpaca=a)
        )
    pos = out["briefing"]["position"]
    assert pos is not None
    assert pos["qty"] == 10
    assert pos["portfolio_weight_frac"] == pytest.approx(1.0)  # only holding in fixture


def test_endpoint_wires_both_clients():
    def market_override():
        m = market_fake()
        try:
            yield m
        finally:
            m.close()

    def alpaca_override():
        a = alpaca_fake()
        try:
            yield a
        finally:
            a.close()

    app.dependency_overrides[get_market_client] = market_override
    app.dependency_overrides[get_alpaca_client] = alpaca_override
    try:
        r = client.get("/api/briefing/AAPL")
        assert r.status_code == 200
        body = r.json()
        assert body["briefing"]["last_close"] == 159.0
        assert body["briefing"]["position"]["qty"] == 10
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------- T023b

def fmp_fake(balance_status=200):
    from test_fmp import fmp_settings

    from data.fmp import FmpClient

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/stable/cash-flow-statement"):
            return httpx.Response(200, json=[{"date": "2025-12-31",
                                              "freeCashFlow": 80000.0}])
        if path.endswith("/stable/balance-sheet-statement"):
            return httpx.Response(balance_status, json=[{
                "date": "2025-12-31", "totalDebt": 50000.0,
                "totalStockholdersEquity": 200000.0, "totalAssets": 400000.0}])
        if path.endswith("/stable/profile"):
            return httpx.Response(200, json=[{"marketCap": 1600000.0}])
        return httpx.Response(404, json={})

    return FmpClient(settings=fmp_settings(), transport=httpx.MockTransport(handler))


def test_briefing_without_fmp_has_null_fundamentals():
    with market_fake() as m:
        out = registry.execute("get_symbol_briefing", {"symbol": "AAPL"},
                               ToolContext(market=m))
    assert out["fundamentals"] is None


def test_briefing_with_fmp_carries_hand_computed_ratios():
    with market_fake() as m, fmp_fake() as f:
        out = registry.execute("get_symbol_briefing", {"symbol": "AAPL"},
                               ToolContext(market=m, fmp=f))
    fund = out["fundamentals"]
    assert fund["available"] is True
    assert fund["fcf_yield"] == pytest.approx(0.05)      # 80k / 1.6M
    assert fund["debt_to_equity"] == pytest.approx(0.25)
    assert fund["debt_to_assets"] == pytest.approx(0.125)
    assert any("fiscal year-end" in n for n in fund["notes"])


def test_briefing_survives_paywalled_balance_sheet():
    """The unprobed endpoint failing must not cost the FCF half (D030)."""
    with market_fake() as m, fmp_fake(balance_status=403) as f:
        out = registry.execute("get_symbol_briefing", {"symbol": "AAPL"},
                               ToolContext(market=m, fmp=f))
    fund = out["fundamentals"]
    assert fund["available"] is True
    assert fund["fcf_yield"] == pytest.approx(0.05)      # FCF half intact
    assert fund["debt_to_equity"] is None
    assert any("balance sheet unavailable" in n for n in fund["notes"])
