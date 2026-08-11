"""GET /api/benchmark — DI-overridden DB + market client; no network."""

from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from test_alpaca import paper_settings

from api.main import app, get_db_session, get_market_client
from data.db import make_engine, make_session_factory
from data.market_data import MarketDataClient
from data.models import AccountSnapshot, Base, BrokerAccount

client = TestClient(app)

BARS = {
    "symbol": "SPY",
    "next_page_token": None,
    "bars": [
        {"t": "2026-08-01T04:00:00Z", "o": 1, "h": 1, "l": 1, "c": 500.0, "v": 1},
        {"t": "2026-08-02T04:00:00Z", "o": 1, "h": 1, "l": 1, "c": 505.0, "v": 1},
    ],
}


def seeded_db_override():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as s:
        acct = BrokerAccount(broker="alpaca-paper", external_id="A1")
        s.add(acct)
        s.flush()
        for day, equity in ((1, 100000.0), (2, 101000.0)):
            s.add(AccountSnapshot(
                account_id=acct.id, equity=equity, cash=0.0, buying_power=0.0,
                asof=datetime(2026, 8, day, 16, 0, 0, tzinfo=timezone.utc),
                source="alpaca-paper",
            ))
        s.commit()
        yield s
    engine.dispose()


def market_override():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BARS)

    c = MarketDataClient(settings=paper_settings(), transport=httpx.MockTransport(handler))
    try:
        yield c
    finally:
        c.close()


def test_benchmark_compares_aligned_series():
    app.dependency_overrides[get_db_session] = seeded_db_override
    app.dependency_overrides[get_market_client] = market_override
    try:
        r = client.get("/api/benchmark", params={"symbol": "SPY", "days": 30})
        assert r.status_code == 200
        body = r.json()
        assert body["dates"] == ["2026-08-01", "2026-08-02"]
        m = body["metrics"]
        assert m["portfolio"]["cumulative_return"] == pytest.approx(0.01)
        assert m["benchmark"]["cumulative_return"] == pytest.approx(0.01)
        assert m["excess_return"] == pytest.approx(0.0)
        assert body["source"].startswith("snapshots + alpaca-data")
        assert body["asof"]
    finally:
        app.dependency_overrides.clear()


def test_benchmark_409_when_no_overlap():
    def empty_db():
        engine = make_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with make_session_factory(engine)() as s:
            yield s
        engine.dispose()

    app.dependency_overrides[get_db_session] = empty_db
    app.dependency_overrides[get_market_client] = market_override
    try:
        r = client.get("/api/benchmark")
        assert r.status_code == 409
        assert "sync" in r.json()["detail"]
    finally:
        app.dependency_overrides.clear()
