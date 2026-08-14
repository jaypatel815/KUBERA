"""get_news (D022) — client parsing, tool execution, endpoint. All MockTransport;
the live Alpaca news feed is not reachable from the sandbox (same as market data).
"""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from test_alpaca import paper_settings

from api.main import app, get_market_client
from api.tools import ToolContext, ToolError, registry
from data.market_data import MarketDataClient

client = TestClient(app)

_RECENT = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
_OLD = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()

NEWS_JSON = {
    "news": [
        {
            "id": 1, "headline": "Fed holds rates steady", "author": "a",
            "created_at": _RECENT, "updated_at": _RECENT,
            "summary": "The Federal Reserve held its benchmark rate. " * 30,  # long
            "url": "https://example.com/fed", "symbols": ["spy", "QQQ"],
            "source": "benzinga",
        },
        {
            "id": 2, "headline": "Chipmaker beats estimates", "author": "b",
            "created_at": _OLD, "updated_at": _OLD,
            "summary": "", "url": None, "symbols": [],
            "source": None,
        },
    ],
    "next_page_token": None,
}


def news_fake(captured: dict | None = None) -> MarketDataClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if captured is not None:
            captured["url"] = str(request.url)
        assert "/v1beta1/news" in request.url.path
        return httpx.Response(200, json=NEWS_JSON)

    return MarketDataClient(settings=paper_settings(),
                            transport=httpx.MockTransport(handler))


def test_client_parses_and_normalizes():
    captured: dict = {}
    with news_fake(captured) as m:
        d = m.get_news(["spy", "aapl"], limit=5)
    assert "symbols=SPY%2CAAPL" in captured["url"] or "symbols=SPY,AAPL" in captured["url"]
    assert d.symbols == ["SPY", "AAPL"]
    assert d.source == "alpaca-news"
    first, second = d.items
    assert first.headline == "Fed holds rates steady"
    assert len(first.summary) <= 500  # long summaries truncated
    assert first.symbols == ["SPY", "QQQ"]  # uppercased
    assert first.age_human.endswith("h 0m") or first.age_human.endswith("m")
    assert second.source == "unknown" and second.url == ""  # nulls normalized
    assert second.age_human.startswith("3d")  # old news wears its age


def test_client_market_wide_omits_symbols_param():
    captured: dict = {}
    with news_fake(captured) as m:
        d = m.get_news(None, limit=3)
    assert "symbols=" not in captured["url"]
    assert d.symbols == []


def test_client_rejects_bad_limit():
    with news_fake() as m:
        with pytest.raises(ValueError):
            m.get_news(None, limit=0)
        with pytest.raises(ValueError):
            m.get_news(None, limit=51)


def test_tool_executes_and_accepts_single_string_symbol():
    with news_fake() as m:
        out = registry.execute("get_news", {"symbols": "spy"},
                               ToolContext(market=m))
    assert out["symbols"] == ["SPY"]  # I009 lesson: sloppy args normalized
    assert out["items"][0]["age_human"]
    assert out["asof"]


def test_tool_requires_market_context():
    with pytest.raises(ToolError) as exc:
        registry.execute("get_news", {}, ToolContext())
    assert "market" in str(exc.value)


def test_endpoint_with_and_without_symbols():
    def market_override():
        m = news_fake()
        try:
            yield m
        finally:
            m.close()

    app.dependency_overrides[get_market_client] = market_override
    try:
        r = client.get("/api/news?symbols=SPY,QQQ&limit=5")
        assert r.status_code == 200
        body = r.json()
        assert body["symbols"] == ["SPY", "QQQ"]
        assert len(body["items"]) == 2
        r2 = client.get("/api/news")
        assert r2.status_code == 200
        assert r2.json()["symbols"] == []
        assert client.get("/api/news?limit=99").status_code == 422
    finally:
        app.dependency_overrides.clear()
