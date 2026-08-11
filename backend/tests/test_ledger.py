"""Backtest ledger (T034): recorded metrics must equal engine output, filters work,
and the run tool/endpoint execute end-to-end with mock data."""

import httpx
import pytest
from fastapi.testclient import TestClient
from test_alpaca import paper_settings

from api.main import app, get_db_session, get_market_client
from api.tools import ToolArgumentError, ToolContext, registry
from backtest.engine import run_backtest
from backtest.ledger import list_runs, record_run, run_and_record
from backtest.strategies import build_strategy
from data.db import make_engine, make_session_factory
from data.market_data import MarketDataClient
from data.models import Base

client = TestClient(app)

BARS_JSON = {
    "symbol": "SPY",
    "next_page_token": None,
    "bars": [
        {"t": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T04:00:00Z",
         "o": 1, "h": 1, "l": 1, "c": 100.0 * (1.01 ** i), "v": 1}
        for i in range(90)
    ],
}


@pytest.fixture()
def db():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as s:
        yield s
    engine.dispose()


def market_fake() -> MarketDataClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BARS_JSON)

    return MarketDataClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def test_record_and_list_roundtrip(db):
    prices = [100.0, 110.0, 99.0, 108.9]
    dates = ["2026-08-01", "2026-08-02", "2026-08-03", "2026-08-04"]
    result = run_backtest(prices, dates, lambda c: 1.0, "always_long")
    row = record_run(db, result, "spy", {"template": "test"}, 5.0, "alpaca-data-iex")
    assert row.symbol == "SPY"
    assert row.cumulative_return == pytest.approx(result.cumulative_return)
    assert row.max_drawdown_frac == pytest.approx(result.max_drawdown_frac)
    assert row.start_date == "2026-08-01" and row.end_date == "2026-08-04"
    assert row.params_json == '{"template": "test"}'
    runs = list_runs(db)
    assert len(runs) == 1 and runs[0].id == row.id


def test_list_filters(db):
    prices, dates = [100.0, 101.0], ["2026-08-01", "2026-08-02"]
    r = run_backtest(prices, dates, lambda c: 1.0, "strat_a")
    record_run(db, r, "SPY", {}, 0.0, "s")
    r2 = run_backtest(prices, dates, lambda c: 0.0, "strat_b")
    record_run(db, r2, "AAPL", {}, 0.0, "s")
    assert len(list_runs(db, strategy="strat_a")) == 1
    assert len(list_runs(db, symbol="aapl")) == 1
    with pytest.raises(ValueError):
        list_runs(db, limit=0)


def test_run_and_record_with_market(db):
    with market_fake() as m:
        result, row = run_and_record(
            db, m, build_strategy("buy_and_hold"), {"template": "buy_and_hold"}, "SPY",
            days=90, cost_bps=0.0,
        )
    # 90 bars of +1%/bar, invested from bar 1: equity ~ 1.01**89
    assert result.cumulative_return == pytest.approx(1.01**89 - 1, rel=1e-9)
    assert row.bars_count == 90
    assert row.sharpe_ann is not None


def test_tool_rejects_unknown_strategy(db):
    with market_fake() as m:
        with pytest.raises(ToolArgumentError) as exc:
            registry.execute(
                "run_backtest", {"strategy": "nope"}, ToolContext(db=db, market=m)
            )
    assert "valid:" in str(exc.value)


def test_api_run_then_list():
    # StaticPool: one shared connection, so the TestClient's request threads see the
    # same in-memory database the test created tables in.
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)

    def db_override():
        with factory() as s:
            yield s

    def market_override():
        m = market_fake()
        try:
            yield m
        finally:
            m.close()

    app.dependency_overrides[get_db_session] = db_override
    app.dependency_overrides[get_market_client] = market_override
    try:
        r = client.post("/api/backtests/run", params={"strategy": "momentum", "days": 90})
        assert r.status_code == 200
        body = r.json()
        assert body["strategy"] == "momentum_60"
        assert body["run_id"] >= 1
        listing = client.get("/api/backtests")
        assert listing.status_code == 200
        assert listing.json()["count"] == 1
        bad = client.post("/api/backtests/run", params={"strategy": "nope"})
        assert bad.status_code == 422
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
