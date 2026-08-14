"""Paper loop (T032) — every path hand-computed: order, reject, no-action, breaker.
No network; MockTransport + in-memory DB. Equity 100k, default risk cap 20% = 20k."""

import httpx
import pytest
from sqlalchemy import select
from test_alpaca import paper_settings

from backtest.paper_loop import run_paper_cycle
from data.alpaca import AlpacaClient
from data.db import make_engine, make_session_factory
from data.market_data import MarketDataClient
from data.models import Base, SignalLog
from risk.engine import RiskEngine

BARS_JSON = {
    "symbol": "SPY",
    "next_page_token": None,
    "bars": [
        # +1/day with ±1 H/L margins -> every true range is exactly 2.0 -> ATR = 2.0,
        # so the T078 vol-parity ceiling is 1% * 100k / (2 * 2.0) * 179 = 44,750 —
        # comfortably above every delta in these tests: legacy expectations unchanged.
        {"t": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T04:00:00Z",
         "o": 100.0 + i, "h": 101.0 + i, "l": 99.0 + i, "c": 100.0 + i, "v": 1}
        for i in range(80)  # rising: momentum(lookback<=78) will be long; last close 179
    ],
}

ORDER_RESPONSE = {"id": "ord-123", "symbol": "SPY", "qty": "83.799", "side": "buy",
                  "status": "accepted"}


def account_json(equity=100_000.0):
    return {"account_number": "PA1TEST23", "status": "ACTIVE", "currency": "USD",
            "cash": str(equity), "equity": str(equity), "buying_power": str(equity)}


class FakeBroker:
    """Routing MockTransport handler that records order POSTs."""

    def __init__(self, equity=100_000.0, positions=None):
        self.equity = equity
        self.positions = positions or []
        self.order_posts: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v2/orders" and request.method == "POST":
            import json
            self.order_posts.append(json.loads(request.content))
            return httpx.Response(200, json=ORDER_RESPONSE)
        if "/v2/account" in request.url.path:
            return httpx.Response(200, json=account_json(self.equity))
        if "/v2/positions" in request.url.path:
            return httpx.Response(200, json=self.positions)
        if "/bars" in request.url.path:
            return httpx.Response(200, json=BARS_JSON)
        return httpx.Response(404, json={})


def position_json(symbol="SPY", qty=10.0, market_value=1790.0):
    return {"symbol": symbol, "qty": str(qty), "avg_entry_price": "100",
            "current_price": "179", "market_value": str(market_value),
            "cost_basis": "1000", "unrealized_pl": "790", "unrealized_plpc": "0.79"}


@pytest.fixture()
def db():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as s:
        yield s
    engine.dispose()


def run_cycle(db, broker: FakeBroker, risk=None, allocation=0.15, strategy=None):
    strategy = strategy or (lambda closes: 1.0)
    strategy.__name__ = getattr(strategy, "__name__", "always_long")
    transport = httpx.MockTransport(broker)
    with AlpacaClient(settings=paper_settings(), transport=transport) as alpaca, \
         MarketDataClient(settings=paper_settings(), transport=transport) as market:
        return run_paper_cycle(db, alpaca, market, risk or RiskEngine(), strategy, "SPY",
                               allocation_frac=allocation)


def test_buy_path_hand_computed(db):
    broker = FakeBroker()
    r = run_cycle(db, broker, allocation=0.15)
    # target = 1.0 * 0.15 * 100k = 15000; current 0; delta 15000; qty = 15000/179 = 83.799
    assert r.action == "ordered"
    assert r.target_value == pytest.approx(15_000.0)
    assert len(broker.order_posts) == 1
    assert broker.order_posts[0]["side"] == "buy"
    assert float(broker.order_posts[0]["qty"]) == pytest.approx(15_000 / 179.0, abs=1e-3)
    row = db.execute(select(SignalLog)).scalar_one()
    assert row.action == "ordered"
    assert row.order_external_id == "ord-123"
    assert row.ts.tzinfo is not None and row.bars_asof.tzinfo is not None


def test_risk_cap_rejection_no_order_sent(db):
    broker = FakeBroker()
    r = run_cycle(db, broker, allocation=0.50)  # target 50k > 20k cap
    assert r.action == "rejected"
    assert "position cap" in r.detail
    assert broker.order_posts == []  # nothing reached the broker
    row = db.execute(select(SignalLog)).scalar_one()
    assert row.action == "rejected"
    assert "position cap" in (row.reasons or "")


def test_no_action_when_at_target(db):
    # held 15000 == target 15000 -> delta 0 < min trade
    broker = FakeBroker(positions=[position_json(qty=83.8, market_value=15_000.0)])
    r = run_cycle(db, broker, allocation=0.15)
    assert r.action == "no_action"
    assert broker.order_posts == []
    assert db.execute(select(SignalLog)).scalar_one().action == "no_action"


def test_sell_path_capped_at_held_qty(db):
    # weight 0 -> target 0; held 10 shares worth 1790 -> sell exactly 10 (1790/179)
    broker = FakeBroker(positions=[position_json(qty=10.0, market_value=1790.0)])
    flat = lambda closes: 0.0  # noqa: E731
    flat.__name__ = "always_flat"
    r = run_cycle(db, broker, strategy=flat)
    assert r.action == "ordered"
    assert broker.order_posts[0]["side"] == "sell"
    assert float(broker.order_posts[0]["qty"]) == pytest.approx(10.0)


def test_circuit_breaker_blocks_second_cycle(db):
    risk = RiskEngine()
    broker_day_start = FakeBroker(equity=100_000.0)
    r1 = run_cycle(db, broker_day_start, risk=risk, allocation=0.15)
    assert r1.action == "ordered"
    # equity collapses 4% same day -> breaker trips inside the cycle -> rejection
    broker_crash = FakeBroker(equity=96_000.0)
    r2 = run_cycle(db, broker_crash, risk=risk, allocation=0.15)
    assert risk.tripped
    assert r2.action == "rejected"
    assert "halted" in r2.detail
    assert broker_crash.order_posts == []
    actions = [row.action for row in db.execute(select(SignalLog)).scalars()]
    assert actions == ["ordered", "rejected"]


def test_bad_allocation_rejected(db):
    with pytest.raises(ValueError):
        run_cycle(db, FakeBroker(), allocation=0.0)
