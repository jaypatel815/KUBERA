"""Tests for /api/market endpoints — deterministic, no network."""

import httpx
from fastapi.testclient import TestClient
from test_alpaca import paper_settings
from test_market_data import BARS_JSON, QUOTE_JSON, TRADE_JSON

from api.main import app, get_market_client
from data.market_data import MarketDataClient

client = TestClient(app)


def override_with(routes: dict):
    """Build a get_market_client override backed by a MockTransport routing table."""

    def _override():
        def handler(request: httpx.Request) -> httpx.Response:
            for fragment, payload in routes.items():
                if fragment in request.url.path:
                    return httpx.Response(200, json=payload)
            return httpx.Response(404, json={"message": "not found"})

        c = MarketDataClient(settings=paper_settings(), transport=httpx.MockTransport(handler))
        try:
            yield c
        finally:
            c.close()

    return _override


def test_market_latest_combines_trade_and_quote():
    app.dependency_overrides[get_market_client] = override_with(
        {"/trades/latest": TRADE_JSON, "/quotes/latest": QUOTE_JSON}
    )
    try:
        r = client.get("/api/market/AAPL/latest")
        assert r.status_code == 200
        body = r.json()
        assert body["trade"]["price"] == 229.83
        assert body["quote"]["ask"] == 229.85
        for part in ("trade", "quote"):
            assert body[part]["exchange_ts"]
            assert body[part]["asof"]
            assert body[part]["source"] == "alpaca-data-iex"
    finally:
        app.dependency_overrides.clear()


def test_market_bars_days_validation():
    app.dependency_overrides[get_market_client] = override_with({"/bars": BARS_JSON})
    try:
        ok = client.get("/api/market/AAPL/bars", params={"days": 5})
        assert ok.status_code == 200
        assert len(ok.json()["bars"]) == 2
        bad = client.get("/api/market/AAPL/bars", params={"days": 0})
        assert bad.status_code == 422
    finally:
        app.dependency_overrides.clear()
