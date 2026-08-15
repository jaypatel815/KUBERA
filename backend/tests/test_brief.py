"""Briefs & reviews (T062) — composition hand-checked with seeded DB + fake broker;
graceful degradation; tool arg validation; endpoint smoke (StaticPool)."""

from datetime import datetime, timezone

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from test_alpaca import paper_settings
from test_paper_loop import BARS_JSON, account_json, position_json

from api.brief import compose_eod_report, compose_morning_brief, compose_weekly_review
from api.main import app
from api.tools import ToolArgumentError, ToolContext, registry
from data.alpaca import AlpacaClient
from data.market_data import MarketDataClient
from data.models import AccountSnapshot, Base, BrokerAccount, SignalLog
from risk.engine import RiskEngine
from risk.persistence import persist_risk_state


def fresh_trade_json(price=185.0):
    return {"symbol": "SPY",
            "trade": {"t": datetime.now(timezone.utc).isoformat(), "p": price, "s": 1}}


def route(equity=100_000.0, positions=None, trade_price=185.0):
    def handler(request: httpx.Request) -> httpx.Response:
        p = request.url.path
        if "/v2/account" in p:
            return httpx.Response(200, json=account_json(equity))
        if "/v2/positions" in p:
            return httpx.Response(200, json=positions or [])
        if "/trades/latest" in p:
            return httpx.Response(200, json=fresh_trade_json(trade_price))
        if "/bars" in p:
            return httpx.Response(200, json=BARS_JSON)
        return httpx.Response(404, json={})
    return handler


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def clients(handler):
    transport = httpx.MockTransport(handler)
    return (AlpacaClient(settings=paper_settings(), transport=transport),
            MarketDataClient(settings=paper_settings(), transport=transport))


def _seed_day(db, start=100_000.0):
    risk = RiskEngine()
    risk.start_day(start, datetime.now(timezone.utc).date().isoformat())
    persist_risk_state(db, risk)


def _seed_row(db, action, reasons=None):
    db.add(SignalLog(
        strategy="s", symbol="SPY", signal_weight=1.0, equity=100_000.0,
        current_value=0.0, target_value=1000.0, action=action, reasons=reasons,
        order_external_id=None, bars_asof=datetime.now(timezone.utc), source="t",
        ts=datetime.now(timezone.utc),
    ))
    db.commit()


def test_morning_brief_hand(db):
    _seed_day(db)
    alpaca, market = clients(route(
        positions=[position_json(qty=10.0, market_value=1790.0)]))
    with alpaca, market:
        b = compose_morning_brief(db, alpaca, market)
    assert b["type"] == "morning"
    assert [s["symbol"] for s in b["symbols"]] == ["SPY"]  # held ∪ {SPY}
    s = b["symbols"][0]
    # daily close 179 (fixture), fresh latest trade 185 -> gap +3.3520%
    assert s["overnight_gap_frac"] == pytest.approx(185.0 / 179.0 - 1.0)
    assert s["latest_stale"] is False
    assert s["regime"]["regime"] in ("trending_up", "breakout_watch", "range_bound")
    assert s["expected_move_5d"] is not None
    assert "nearest_support" in s and "nearest_resistance" in s
    assert b["risk"]["dqs"]["score"] == 100.0
    # T062b: sections present and honest in the degraded/empty state
    assert b["watchlist"]["note"] == "watchlist is empty"
    assert "FRED_API_KEY" in b["event_risk"]["note"]  # no fred client passed


def test_morning_brief_watchlist_and_events(db):
    from test_macro import fred_settings

    from data.watchlist import add_symbol
    _seed_day(db)
    add_symbol(db, "SPY", "core index thesis")
    # the composer judges "today" in UTC — the fixture must too (local date can lag)
    utc_today = datetime.now(timezone.utc).date().isoformat()

    def fred_handler(request: httpx.Request) -> httpx.Response:
        assert "/fred/release/dates" in request.url.path
        return httpx.Response(200, json={"release_dates": [{"date": utc_today}]})

    from data.fred import FredClient
    alpaca, market = clients(route(
        positions=[position_json(qty=10.0, market_value=1790.0)]))
    fred = FredClient(settings=fred_settings(),
                      transport=httpx.MockTransport(fred_handler))
    with alpaca, market, fred:
        b = compose_morning_brief(db, alpaca, market, fred=fred)
    wl = b["watchlist"]
    assert wl["note"] is None
    assert wl["setups"][0]["symbol"] == "SPY"
    assert wl["setups"][0]["thesis"] == "core index thesis"  # owner's words survive
    ev = b["event_risk"]
    assert ev["note"] is None
    assert ev["upcoming"][0]["days_away"] == 0  # release today, surfaced with date


def test_eod_report_hand(db):
    _seed_day(db, start=100_000.0)
    _seed_row(db, "ordered")
    _seed_row(db, "no_trade", reasons="no trade today: quiet market")
    alpaca, market = clients(route(equity=99_000.0))
    with alpaca, market:
        b = compose_eod_report(db, alpaca)
    assert b["account"]["day_pl_frac"] == pytest.approx(-0.01)
    assert b["risk"]["tier"]["level"] == 1  # 1% loss = 33% of the 3% budget
    assert b["activity"]["counts"] == {"ordered": 1, "no_trade": 1}
    assert len(b["activity"]["decisions"]) == 2
    assert b["activity"]["decisions"][1]["reasons"].startswith("no trade today")


def test_weekly_review_hand(db):
    acct = BrokerAccount(broker="alpaca-paper", external_id="A1")
    db.add(acct)
    db.flush()
    for day, equity in ((1, 100_000.0), (2, 102_000.0)):
        db.add(AccountSnapshot(
            account_id=acct.id, equity=equity, cash=0.0, buying_power=0.0,
            asof=datetime(2026, 1, day, 16, 0, 0, tzinfo=timezone.utc),
            source="alpaca-paper"))
    db.commit()
    _seed_row(db, "ordered")
    _seed_row(db, "no_trade", reasons="no trade today: risk tier 3")
    alpaca, market = clients(route())
    with alpaca, market:
        b = compose_weekly_review(db, alpaca, market)
    perf = b["performance"]
    assert perf["available"] is True
    assert perf["return_frac"] == pytest.approx(0.02)
    # SPY over the same 2 dates: 100 -> 101 = +1%; excess = +1%
    assert perf["benchmark"]["return_frac"] == pytest.approx(0.01)
    assert perf["benchmark"]["excess_return_frac"] == pytest.approx(0.01)
    assert b["discipline"]["no_trades"] == 1
    assert b["discipline"]["tier_restrictions"] == 1
    assert len(b["facts_for_lessons"]) >= 3
    assert "never invent numbers" in b["narration_rule"]


def test_weekly_degrades_without_snapshots(db):
    alpaca, market = clients(route())
    with alpaca, market:
        b = compose_weekly_review(db, alpaca, market)
    assert b["performance"]["available"] is False
    assert "sync" in b["performance"]["why"]


def test_brief_tool_validates_type(db):
    alpaca, market = clients(route())
    with alpaca, market, pytest.raises(ToolArgumentError):
        registry.execute("get_brief", {"type": "hourly"},
                         ToolContext(alpaca=alpaca, market=market, db=db))


def test_brief_endpoint(db):
    from fastapi.testclient import TestClient

    from api import main as main_module

    _seed_day(db)
    handler = route(equity=99_000.0)

    def fake_alpaca():
        with AlpacaClient(settings=paper_settings(),
                          transport=httpx.MockTransport(handler)) as a:
            yield a

    def fake_market():
        with MarketDataClient(settings=paper_settings(),
                              transport=httpx.MockTransport(handler)) as m:
            yield m

    app.dependency_overrides[main_module.get_alpaca_client] = fake_alpaca
    app.dependency_overrides[main_module.get_market_client] = fake_market
    app.dependency_overrides[main_module.get_db_session] = lambda: db
    try:
        client = TestClient(app)
        ok = client.get("/api/brief", params={"type": "eod"})
        bad = client.get("/api/brief", params={"type": "hourly"})
    finally:
        app.dependency_overrides.pop(main_module.get_alpaca_client)
        app.dependency_overrides.pop(main_module.get_market_client)
        app.dependency_overrides.pop(main_module.get_db_session)
    assert ok.status_code == 200 and ok.json()["type"] == "eod"
    assert bad.status_code == 422
