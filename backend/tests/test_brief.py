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

from analysis.market_time import market_today
from api.brief import compose_eod_report, compose_morning_brief, compose_weekly_review
from api.main import app
from api.tools import ToolArgumentError, ToolContext, registry
from data.alpaca import AlpacaClient
from data.market_data import MarketDataClient
from data.models import AccountSnapshot, Base, BrokerAccount, SignalLog, Transaction
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
    risk.start_day(start, market_today().isoformat())  # T111
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
    # T111: the composer judges "today" at the MARKET — the fixture must too
    utc_today = market_today().isoformat()

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


# --- T091b: EOD regime line + weekly attribution section ------------------------

def test_eod_carries_the_regime_attribution_line(db):
    _seed_day(db)
    for action, regime in (("ordered", "trending_up"), ("no_trade", "trending_up"),
                           ("no_trade", "range_bound"), ("rejected", None)):
        db.add(SignalLog(
            strategy="s", symbol="SPY", signal_weight=1.0, equity=100_000.0,
            current_value=0.0, target_value=1000.0, action=action,
            bars_asof=datetime.now(timezone.utc), source="t",
            regime_label=regime, ts=datetime.now(timezone.utc),
        ))
    db.commit()
    alpaca, market = clients(route())
    with alpaca, market:
        out = compose_eod_report(db, alpaca)
    ra = out["regime_attribution"]
    assert ra["by_regime"]["trending_up"] == {"ordered": 1, "no_trade": 1}
    assert ra["by_regime"]["range_bound"] == {"no_trade": 1}
    assert ra["by_regime"]["untagged"] == {"rejected": 1}
    assert ra["dominant_regime"] == "trending_up"
    assert "AT DECISION TIME" in ra["note"]


def test_weekly_attribution_section_and_facts(db):
    now = datetime.now(timezone.utc)
    _seed_day(db)
    db.add(SignalLog(
        strategy="s", symbol="SPY", signal_weight=1.0, equity=100_000.0,
        current_value=0.0, target_value=1000.0, action="ordered",
        order_external_id="ord-1", bars_asof=now, source="t",
        regime_label="trending_up", sub_strategy="momentum",
        entry_bucket="midday", ts=now,
    ))
    db.add(Transaction(account_id=1, external_id="w1", symbol="SPY", side="buy",
                       qty=10.0, price=100.0, occurred_at=now, source="t",
                       order_id="ord-1"))
    db.add(Transaction(account_id=1, external_id="w2", symbol="SPY", side="sell",
                       qty=10.0, price=106.0, occurred_at=now, source="t",
                       order_id="ord-1"))
    db.commit()
    alpaca, market = clients(route())
    with alpaca, market:
        out = compose_weekly_review(db, alpaca, market)
    att = out["attribution"]
    assert att["available"] is True
    assert att["round_trips"] == 1
    assert att["realized_pnl"] == pytest.approx(60.0)
    assert att["by_regime"]["trending_up"]["realized_pnl"] == pytest.approx(60.0)
    assert att["holding_periods"]["by_bucket"]  # populated, shape from T091b
    # route() has no /quotes/latest -> cost estimate degrades to None, no error
    assert att["cost_decomposition"] is None
    assert any("closed round trips realized" in f for f in out["facts_for_lessons"])


def test_weekly_attribution_degrades_without_fills(db):
    _seed_day(db)
    alpaca, market = clients(route())
    with alpaca, market:
        out = compose_weekly_review(db, alpaca, market)
    assert out["attribution"]["available"] is False
    assert "sync.py" in out["attribution"]["why"]


# ---- T142: D021 governance countdown ---------------------------------------
# Pure and frozen-date tested: the packet (d021_evidence.py) existed but the
# weekly review never TOLD the owner to run it. Window = 10 days before the
# ~2026-09-12 revisit; past-due stays visible until the decision is recorded.

def test_d021_countdown_silent_outside_window():
    from datetime import date

    from api.brief import d021_countdown
    assert d021_countdown(date(2026, 8, 21)) is None  # 22 days out


def test_d021_countdown_speaks_inside_window():
    from datetime import date

    from api.brief import d021_countdown
    out = d021_countdown(date(2026, 9, 2))  # exactly 10 days out
    assert out is not None and out["days_until"] == 10
    assert "scripts/d021_evidence.py" in out["line"]
    on_day = d021_countdown(date(2026, 9, 12))
    assert on_day is not None and on_day["days_until"] == 0


def test_d021_countdown_past_due_stays_loud():
    from datetime import date

    from api.brief import d021_countdown
    out = d021_countdown(date(2026, 9, 15))
    assert out is not None and out["days_until"] == -3
    assert "PAST" in out["line"] and "DECISIONS.md" in out["line"]


def test_weekly_carries_governance_key(db):
    # the key is always present (None outside the window) so schedulers can
    # key on it without probing for existence
    _seed_day(db)
    alpaca, market = clients(route())
    with alpaca, market:
        out = compose_weekly_review(db, alpaca, market)
    assert "governance_d021" in out
    g = out["governance_d021"]
    if g is not None:
        assert any(g["line"] in f for f in out["facts_for_lessons"])


# ---- T149: campaign section — counts and dates ONLY (T133 anti-peek) --------

def _seed_campaign(db, attempts=1, forecast_dates=(), window=("2026-08-24", "2026-10-02")):
    import json

    from data.models import ExperimentBudget, HoldoutWindow, ResearchForecast
    db.add(ExperimentBudget(revision="kronos-v1", max_attempts=3,
                            attempts_json=json.dumps(
                                [{"n": i + 1} for i in range(attempts)])))
    db.add(HoldoutWindow(name="kronos-v1-fwd", symbols_json='["SPY"]',
                         start=window[0], end=window[1],
                         params_hash="abcd1234abcd1234", state="frozen"))
    for d in forecast_dates:
        db.add(ResearchForecast(revision="kronos-v1", symbol="SPY",
                                forecast_date=d, basis_close=100.0,
                                p05_frac=-0.01, p50_frac=0.0, p95_frac=0.01,
                                up_odds=0.5, source_note="test fixture"))
    db.commit()


def test_campaign_section_silent_before_any_attempt(db):
    from datetime import date

    from api.brief import campaign_section
    _seed_campaign(db, attempts=0)
    assert campaign_section(db, date(2026, 8, 25)) is None


def test_campaign_section_in_window_counts_and_nudges(db):
    from datetime import date

    from api.brief import campaign_section
    _seed_campaign(db, attempts=1,
                   forecast_dates=("2026-08-24", "2026-08-25"))
    out = campaign_section(db, date(2026, 8, 25))
    c = out["campaigns"][0]
    assert c["attempts"] == "1/3" and c["forecast_days_logged"] == 2
    assert c["days_remaining"] == (date(2026, 10, 2) - date(2026, 8, 25)).days
    assert "nudge" not in c  # today's forecast IS logged
    # anti-peek: no outcome-shaped fields ride the payload
    assert not any(k for k in c if "return" in k or "coverage" in k or "pnl" in k)
    # next morning with no new forecast: the nudge fires
    c2 = campaign_section(db, date(2026, 8, 26))["campaigns"][0]
    assert "coverage lost forever" in c2["nudge"]


def test_campaign_section_pre_and_post_window_lines(db):
    from datetime import date

    from api.brief import campaign_section
    _seed_campaign(db, attempts=1)
    pre = campaign_section(db, date(2026, 8, 21))["campaigns"][0]
    assert pre["status_line"] == "window opens 2026-08-24"
    post = campaign_section(db, date(2026, 10, 5))["campaigns"][0]
    assert "score --consume" in post["status_line"]


def test_morning_brief_carries_campaign_key(db):
    _seed_day(db)
    alpaca, market = clients(route())
    with alpaca, market:
        b = compose_morning_brief(db, alpaca, market)
    assert "research_campaign" in b  # None here (no attempts in fixture DB)


# ---- T150: the week's risk events, surfaced in the weekly review ------------

def test_weekly_risk_events_quiet_week_is_a_stated_fact(db):
    _seed_day(db)
    alpaca, market = clients(route())
    with alpaca, market:
        out = compose_weekly_review(db, alpaca, market)
    rw = out["risk_events_week"]
    assert rw["tier_changes"] == 0 and rw["breaker_trips"] == 0
    assert rw["last_event"] is None
    assert any("no risk events recorded this week" in f
               for f in out["facts_for_lessons"])


def test_weekly_risk_events_counts_and_quotes_the_last(db):
    from datetime import datetime, timezone

    from data.models import RiskEvent
    _seed_day(db)
    db.add(RiskEvent(ts=datetime.now(timezone.utc), kind="tier_change",
                     detail="level=1 cautious (budget 27% consumed)"))
    db.add(RiskEvent(ts=datetime.now(timezone.utc), kind="breaker_trip",
                     detail="daily loss limit hit"))
    db.commit()
    alpaca, market = clients(route())
    with alpaca, market:
        out = compose_weekly_review(db, alpaca, market)
    rw = out["risk_events_week"]
    assert rw["tier_changes"] == 1 and rw["breaker_trips"] == 1
    assert "daily loss limit hit" in rw["last_event"]
    assert any("1 tier change(s), 1 breaker trip(s)" in f
               for f in out["facts_for_lessons"])
