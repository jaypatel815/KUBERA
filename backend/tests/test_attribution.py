"""Attribution pack (T091) — FIFO hand-walked, entry buckets, loop tag persistence,
router leg annotation, and the tool joining fills to decisions via order id."""

from datetime import datetime, timezone

import httpx
import pytest
from sqlalchemy import select
from test_alpaca import paper_settings
from test_paper_loop import FakeBroker, db  # noqa: F811, F401

from analysis.attribution import AttributedFill, fifo_attribution
from api.tools import ToolContext, registry
from backtest.paper_loop import _entry_bucket, run_paper_cycle
from backtest.strategies import make_regime_router
from data.alpaca import AlpacaClient
from data.market_data import MarketDataClient
from data.models import SignalLog, Transaction
from risk.engine import RiskEngine

# --- FIFO attribution: hand-walked --------------------------------------------

def _f(side, qty, price, ts, regime=None, leg=None, bucket=None, symbol="SPY"):
    return AttributedFill(symbol=symbol, side=side, qty=qty, price=price,
                          ts_iso=ts, regime=regime, sub_strategy=leg,
                          entry_bucket=bucket)


def test_fifo_hand_walked():
    fills = [
        _f("buy", 10, 100.0, "2026-08-01T14:00", regime="trending_up",
           leg="momentum", bucket="midday"),
        _f("buy", 5, 110.0, "2026-08-02T14:00", regime="range_bound",
           leg="range", bucket="first_hour"),
        _f("sell", 12, 120.0, "2026-08-03T14:00"),
    ]
    r = fifo_attribution(fills)
    # sell consumes 10 from lot1 (+200 -> trending_up) and 2 from lot2 (+20 -> range)
    assert r.round_trips == 2
    assert r.realized_pnl == pytest.approx(220.0)
    assert r.by_regime["trending_up"]["realized_pnl"] == pytest.approx(200.0)
    assert r.by_regime["range_bound"]["realized_pnl"] == pytest.approx(20.0)
    assert r.by_regime["trending_up"]["win_rate"] == pytest.approx(1.0)
    assert r.by_sub_strategy["momentum"]["round_trips"] == 1
    assert r.by_entry_bucket["midday"]["realized_pnl"] == pytest.approx(200.0)
    # 3 shares of lot2 remain open at 110
    assert r.open_lots == [{"symbol": "SPY", "qty": 3, "price": 110.0,
                            "regime": "range_bound", "sub_strategy": "range",
                            "bucket": "first_hour"}]
    assert r.oversold == []
    assert "sample size" in r.note


def test_fifo_unattributed_and_oversold():
    fills = [
        _f("buy", 5, 100.0, "t1"),                 # no tags: manual trade
        _f("sell", 8, 90.0, "t2"),                 # 5 close the lot, 3 oversold
    ]
    r = fifo_attribution(fills)
    assert r.by_regime["unattributed"]["realized_pnl"] == pytest.approx(-50.0)
    assert r.by_regime["unattributed"]["win_rate"] == 0.0
    assert len(r.oversold) == 1 and r.oversold[0]["qty"] == pytest.approx(3)
    with pytest.raises(ValueError, match="side"):
        fifo_attribution([_f("hold", 1, 1.0, "t")])


# --- entry buckets: boundary-walked --------------------------------------------

@pytest.mark.parametrize("utc_iso, bucket", [
    ("2026-08-13T13:29:00+00:00", "pre"),         # 09:29 ET
    ("2026-08-13T13:31:00+00:00", "first_hour"),  # 09:31 ET
    ("2026-08-13T14:30:00+00:00", "midday"),      # 10:30 ET boundary
    ("2026-08-13T18:30:00+00:00", "last_90"),     # 14:30 ET boundary
    ("2026-08-13T20:01:00+00:00", "post"),        # 16:01 ET
])
def test_entry_buckets(utc_iso, bucket):
    assert _entry_bucket(datetime.fromisoformat(utc_iso)) == bucket


# --- the loop persists tags; the router names its leg ---------------------------

def test_loop_persists_attribution_tags(db):  # noqa: F811
    broker = FakeBroker()
    strategy = lambda closes: 1.0  # noqa: E731
    strategy.__name__ = "always_long"
    transport = httpx.MockTransport(broker)
    with AlpacaClient(settings=paper_settings(), transport=transport) as alpaca, \
         MarketDataClient(settings=paper_settings(), transport=transport) as market:
        r = run_paper_cycle(db, alpaca, market, RiskEngine(), strategy, "SPY",
                            allocation_frac=0.15)
    assert r.action == "ordered"
    row = db.execute(select(SignalLog)).scalar_one()
    assert row.regime_label in ("trending_up", "trending_down", "range_bound",
                                "breakout_watch")  # classified + persisted
    assert row.entry_bucket in ("pre", "first_hour", "midday", "last_90", "post")
    assert row.sub_strategy is None  # plain strategy has no legs


def test_router_annotates_its_leg():
    closes = [100.0 * 1.01**i for i in range(120)]
    router = make_regime_router(lookback=40, momentum_lookback=10)
    router(closes)
    assert router.last_leg == "momentum"  # monotone bull routed to the momentum leg
    chop = [100.0 if i % 2 == 0 else 82.0 for i in range(120)]
    router(chop)
    assert router.last_leg == "range"


# --- the tool joins fills to decisions via order id -----------------------------

def test_get_attribution_tool_join(db):  # noqa: F811
    now = datetime.now(timezone.utc)
    db.add(SignalLog(
        strategy="regime_router_40_60", symbol="SPY", signal_weight=1.0,
        equity=100_000.0, current_value=0.0, target_value=15_000.0,
        action="ordered", reasons=None, order_external_id="ord-1",
        bars_asof=now, source="t", regime_label="trending_up",
        sub_strategy="momentum", entry_bucket="midday", ts=now,
    ))
    db.add(Transaction(account_id=1, external_id="act-1", symbol="SPY", side="buy",
                       qty=10.0, price=100.0, occurred_at=now, source="t",
                       order_id="ord-1"))
    db.add(Transaction(account_id=1, external_id="act-2", symbol="SPY", side="sell",
                       qty=10.0, price=105.0, occurred_at=now, source="t",
                       order_id="ord-manual"))
    db.commit()

    out = registry.execute("get_attribution", {}, ToolContext(db=db))
    rep = out["attribution"]
    assert rep["round_trips"] == 1
    assert rep["realized_pnl"] == pytest.approx(50.0)
    # the ENTRY's tags own the outcome, joined via ord-1
    assert rep["by_regime"]["trending_up"]["realized_pnl"] == pytest.approx(50.0)
    assert rep["by_sub_strategy"]["momentum"]["round_trips"] == 1
    assert out["activity_by_regime"]["trending_up"]["ordered"] == 1
    assert out["fills_analyzed"] == 2
