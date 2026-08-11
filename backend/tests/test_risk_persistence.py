"""T035: a process restart must NEVER forget a tripped breaker. These tests simulate
restarts with fresh RiskEngine instances against the same DB."""

from datetime import datetime, timezone

import httpx
import pytest
from sqlalchemy import select
from test_alpaca import paper_settings
from test_paper_loop import FakeBroker

from backtest.paper_loop import run_paper_cycle
from data.alpaca import AlpacaClient
from data.db import make_engine, make_session_factory
from data.market_data import MarketDataClient
from data.models import Base, SignalLog
from risk.engine import RiskEngine
from risk.persistence import persist_risk_state, restore_risk_state

NOW = datetime(2026, 8, 11, 15, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def db():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as s:
        yield s
    engine.dispose()


def test_roundtrip_preserves_trip(db):
    e1 = RiskEngine()
    e1.start_day(100_000.0, "2026-08-11")
    e1.record_equity(96_000.0, NOW)  # -4% -> tripped
    assert e1.tripped
    persist_risk_state(db, e1)

    e2 = RiskEngine()  # "restart"
    assert restore_risk_state(db, e2) is True
    assert e2.tripped
    assert e2.trip_reason == e1.trip_reason
    assert e2.day == "2026-08-11"
    assert e2.day_start_equity == pytest.approx(100_000.0)
    assert e2.pre_trade_check.__self__ is not None  # sanity
    from risk.engine import OrderRequest
    d = e2.pre_trade_check(OrderRequest("SPY", "buy", 1, 100.0), 96_000.0, 0.0)
    assert not d.approved


def test_restore_returns_false_when_no_state(db):
    assert restore_risk_state(db, RiskEngine()) is False


def test_reset_persists(db):
    e1 = RiskEngine()
    e1.start_day(100_000.0, "2026-08-11")
    e1.record_equity(96_000.0, NOW)
    persist_risk_state(db, e1)
    e1.reset("owner reviewed and re-enabled")
    persist_risk_state(db, e1)

    e2 = RiskEngine()
    restore_risk_state(db, e2)
    assert not e2.tripped
    assert e2.trip_reason is None


def test_restarted_paper_loop_cannot_bypass_breaker(db):
    """The killer test: trip in one 'process', restart with a fresh engine, still blocked."""
    def cycle(broker, risk):
        transport = httpx.MockTransport(broker)
        with AlpacaClient(settings=paper_settings(), transport=transport) as alpaca, \
             MarketDataClient(settings=paper_settings(), transport=transport) as market:
            strat = lambda closes: 1.0  # noqa: E731
            strat.__name__ = "always_long"
            return run_paper_cycle(db, alpaca, market, risk, strat, "SPY",
                                   allocation_frac=0.15)

    engine1 = RiskEngine()
    assert cycle(FakeBroker(equity=100_000.0), engine1).action == "ordered"
    r2 = cycle(FakeBroker(equity=96_000.0), engine1)  # -4% same day -> trip
    assert engine1.tripped and r2.action == "rejected"

    engine2 = RiskEngine()  # simulated restart: brand-new process state
    broker3 = FakeBroker(equity=96_500.0)
    r3 = cycle(broker3, engine2)
    assert engine2.tripped  # loaded from DB, not from memory
    assert r3.action == "rejected"
    assert broker3.order_posts == []
    actions = [row.action for row in db.execute(select(SignalLog)).scalars()]
    assert actions == ["ordered", "rejected", "rejected"]
