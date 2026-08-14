"""T067 — graduated risk tiers + Decision Quality Score. Tier boundaries and DQS
penalties hand-computed; loop enforcement proven (halving, pausing, sells exempt,
breaker precedence); the get_risk_status tool end-to-end."""

from collections import namedtuple
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import select
from test_alpaca import paper_settings
from test_paper_loop import BARS_JSON, FakeBroker, account_json, db, position_json  # noqa: F401

from api.main import app
from api.tools import ToolContext, registry
from backtest.paper_loop import run_paper_cycle
from data.alpaca import AlpacaClient
from data.market_data import MarketDataClient
from data.models import SignalLog
from risk.dqs import score_decisions
from risk.engine import RiskEngine
from risk.persistence import persist_risk_state
from risk.tiers import current_tier

# --- tiers: boundaries hand-computed (limit 3%, start 100k) -------------------

@pytest.mark.parametrize(
    "equity, level, name",
    [
        (100_000.0, 0, "normal"),
        (101_000.0, 0, "normal"),        # up on the day: budget untouched
        (99_300.0, 0, "normal"),         # -0.70% = 23.3% of budget
        (99_250.0, 1, "caution"),        # -0.75% = exactly 25% (inclusive)
        (98_500.0, 2, "half_size"),      # -1.50% = 50%
        (97_750.0, 3, "entries_paused"),  # -2.25% = 75%
        (97_000.0, 4, "breaker"),        # -3.00% = 100%
    ],
)
def test_tier_boundaries(equity, level, name):
    t = current_tier(100_000.0, equity, 0.03)
    assert (t.level, t.name) == (level, name)


def test_tier_validation():
    with pytest.raises(ValueError):
        current_tier(0.0, 100.0, 0.03)
    with pytest.raises(ValueError):
        current_tier(100.0, 100.0, 1.5)


# --- DQS: each component hand-computed ----------------------------------------

Row = namedtuple("Row", "ts action equity target_value current_value")
NOW = datetime(2026, 8, 13, 20, 0, 0, tzinfo=timezone.utc)


def _row(days_ago, action, equity, delta=1000.0, hours=0):
    return Row(NOW - timedelta(days=days_ago, hours=hours), action, equity, delta, 0.0)


def test_dqs_empty_is_perfect():
    r = score_decisions([], now=NOW)
    assert r.score == 100.0 and "no orders" in r.note


def test_dqs_overtrading_penalty_hand():
    # 12 orders over 2 active days = 6/day vs max 5 -> ratio 1.2 ->
    # penalty min(40, (1.2-0.6)*100) = 40; flat equity + equal sizes: score 60
    rows = [_row(1, "ordered", 100_000.0, hours=h) for h in range(6)]
    rows += [_row(0, "ordered", 100_000.0, hours=h) for h in range(6)]
    r = score_decisions(rows, now=NOW)
    assert r.components["trade_frequency"]["penalty"] == pytest.approx(40.0)
    assert r.components["post_loss_activity"]["penalty"] == pytest.approx(0.0)
    assert r.score == pytest.approx(60.0)


def test_dqs_trading_into_drawdown_hand():
    # 3 of 4 orders placed with equity below the previous row: 0.75*40 = 30
    rows = [
        _row(1, "no_action", 100_000.0, hours=3),
        _row(1, "ordered", 99_000.0, hours=2),   # below prev -> counted
        _row(1, "ordered", 98_000.0, hours=1),   # counted
        _row(0, "ordered", 97_000.0, hours=2),   # counted
        _row(0, "ordered", 97_000.0, hours=1),   # equal, not below
    ]
    r = score_decisions(rows, now=NOW)
    assert r.components["post_loss_activity"]["orders_into_drawdown"] == 3
    assert r.components["post_loss_activity"]["penalty"] == pytest.approx(30.0)
    assert r.components["trade_frequency"]["penalty"] == pytest.approx(0.0)  # 2/day
    assert r.score == pytest.approx(70.0)


def test_dqs_sizing_inconsistency_hand():
    # deltas [1000, 1000, 5000]: cv = 2309.401/2333.333 = 0.98974
    # penalty = (0.48974)*30 = 14.692 -> score 85.3; 3 orders/day = ratio 0.6 -> 0
    rows = [
        _row(0, "ordered", 100_000.0, delta=1000.0, hours=3),
        _row(0, "ordered", 100_000.0, delta=1000.0, hours=2),
        _row(0, "ordered", 100_000.0, delta=5000.0, hours=1),
    ]
    r = score_decisions(rows, now=NOW)
    assert r.components["sizing_consistency"]["cv"] == pytest.approx(0.99, abs=0.001)
    assert r.score == pytest.approx(85.3)


def test_dqs_window_excludes_old_rows_and_counts_restraint():
    rows = [_row(9, "ordered", 100_000.0, hours=h) for h in range(6)]  # outside 7d
    rows += [_row(0, "no_trade", 100_000.0), _row(0, "ordered", 100_000.0, hours=1)]
    r = score_decisions(rows, now=NOW)
    assert r.orders == 1 and r.no_trades == 1
    assert r.score == pytest.approx(100.0)
    assert "restraint" in r.components


# --- loop enforcement ---------------------------------------------------------

def _seed_day(db, start_equity=100_000.0):  # noqa: F811
    risk = RiskEngine()
    today = datetime.now(timezone.utc).date().isoformat()
    risk.start_day(start_equity, today)
    persist_risk_state(db, risk)
    return risk


def run_cycle_at_equity(db, equity, risk, strategy=None, positions=None):  # noqa: F811
    broker = FakeBroker(equity=equity, positions=positions or [])
    strategy = strategy or (lambda closes: 1.0)
    strategy.__name__ = getattr(strategy, "__name__", "always_long")
    transport = httpx.MockTransport(broker)
    with AlpacaClient(settings=paper_settings(), transport=transport) as alpaca, \
         MarketDataClient(settings=paper_settings(), transport=transport) as market:
        result = run_paper_cycle(db, alpaca, market, risk, strategy, "SPY",
                                 allocation_frac=0.15)
    return result, broker


def test_tier2_halves_the_buy(db):  # noqa: F811
    risk = _seed_day(db)
    r, broker = run_cycle_at_equity(db, 98_500.0, risk)  # exactly 50% of budget
    assert r.action == "ordered"
    # target = 0.15 * 98500 = 14775; ceiling not binding; tier 2 halves -> 7387.50
    assert float(broker.order_posts[0]["qty"]) == pytest.approx(7387.5 / 179.0, abs=1e-3)
    assert "risk tier 2" in r.detail and "halved" in r.detail
    row = db.execute(select(SignalLog)).scalars().all()[-1]
    assert "risk tier 2" in (row.reasons or "")


def test_tier3_pauses_entries(db):  # noqa: F811
    risk = _seed_day(db)
    r, broker = run_cycle_at_equity(db, 97_700.0, risk)  # 76.7% of budget
    assert r.action == "no_trade"
    assert "risk tier 3" in r.detail and "entries paused" in r.detail
    assert broker.order_posts == []


def test_tier1_notes_but_trades(db):  # noqa: F811
    risk = _seed_day(db)
    r, broker = run_cycle_at_equity(db, 99_200.0, risk)  # 26.7% of budget
    assert r.action == "ordered"
    assert "risk tier 1" in r.detail
    assert len(broker.order_posts) == 1


def test_tier3_never_blocks_sells(db):  # noqa: F811
    risk = _seed_day(db)
    flat = lambda closes: 0.0  # noqa: E731
    flat.__name__ = "always_flat"
    r, broker = run_cycle_at_equity(
        db, 97_700.0, risk, strategy=flat,
        positions=[position_json(qty=10.0, market_value=1790.0)],
    )
    assert r.action == "ordered" and broker.order_posts[0]["side"] == "sell"


def test_breaker_precedence_over_tiers(db):  # noqa: F811
    # a 4% crash trips the breaker inside the cycle: the gate must REJECT loudly
    # ("halted"), not quietly no_trade via tier logic
    risk = _seed_day(db)
    r, broker = run_cycle_at_equity(db, 96_000.0, risk)
    assert risk.tripped
    assert r.action == "rejected" and "halted" in r.detail
    assert broker.order_posts == []


# --- the risk-status tool -----------------------------------------------------

def test_get_risk_status_tool(db):  # noqa: F811
    _seed_day(db)
    db.add(SignalLog(
        strategy="s", symbol="SPY", signal_weight=1.0, equity=100_000.0,
        current_value=0.0, target_value=1000.0, action="ordered", reasons=None,
        order_external_id="x", bars_asof=datetime.now(timezone.utc), source="t",
        ts=datetime.now(timezone.utc),
    ))
    db.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        if "/v2/account" in request.url.path:
            return httpx.Response(200, json=account_json(98_500.0))
        return httpx.Response(200, json=[])

    with AlpacaClient(settings=paper_settings(),
                      transport=httpx.MockTransport(handler)) as alpaca:
        out = registry.execute("get_risk_status", {},
                               ToolContext(alpaca=alpaca, db=db))
    assert out["tier"]["level"] == 2 and out["tier"]["name"] == "half_size"
    assert out["tier"]["budget_consumed_frac"] == pytest.approx(0.5)
    assert out["breaker"]["tripped"] is False
    assert out["dqs"]["score"] <= 100.0 and out["dqs"]["orders"] == 1
    assert out["asof"]


def test_risk_endpoint():
    # StaticPool: the TestClient's request thread must see the same in-memory DB
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool

    from api import main as main_module
    from data.models import Base

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        _seed_day(session)

        def handler(request: httpx.Request) -> httpx.Response:
            if "/v2/account" in request.url.path:
                return httpx.Response(200, json=account_json(100_000.0))
            return httpx.Response(200, json=[])

        def fake_alpaca():
            with AlpacaClient(settings=paper_settings(),
                              transport=httpx.MockTransport(handler)) as a:
                yield a

        app.dependency_overrides[main_module.get_alpaca_client] = fake_alpaca
        app.dependency_overrides[main_module.get_db_session] = lambda: session
        try:
            from fastapi.testclient import TestClient
            r = TestClient(app).get("/api/risk")
        finally:
            app.dependency_overrides.pop(main_module.get_alpaca_client)
            app.dependency_overrides.pop(main_module.get_db_session)
    engine.dispose()
    assert r.status_code == 200
    body = r.json()
    assert body["tier"]["level"] == 0
    assert body["dqs"]["score"] == 100.0
