"""T088 execution quality — hand-computed slippage.

Hand cases (decision 100.00):
- BUY filled 100.10  -> paid 0.10 more  -> +10 bps (a COST)
- BUY filled  99.90  -> paid 0.10 less  -> -10 bps (price improvement)
- SELL filled 99.90  -> received less   -> +10 bps (a COST)
- SELL filled 100.10 -> received more   -> -10 bps
Positive always means "this execution cost you", both sides.
"""

from datetime import datetime, timedelta, timezone

import pytest

from analysis.execution import (
    MIN_BUCKET_SAMPLE,
    ExecutionFill,
    execution_report,
    slippage_bps,
)
from api.tools import ToolContext, registry
from data.db import make_engine, make_session_factory
from data.models import Base, SignalLog, Transaction

# --- sign convention ----------------------------------------------------------

@pytest.mark.parametrize("side,fill,expected", [
    ("buy", 100.10, 10.0),
    ("buy", 99.90, -10.0),
    ("sell", 99.90, 10.0),
    ("sell", 100.10, -10.0),
])
def test_slippage_sign_convention(side, fill, expected):
    assert slippage_bps(100.0, fill, side) == pytest.approx(expected)


def test_slippage_validation():
    with pytest.raises(ValueError):
        slippage_bps(0, 100, "buy")
    with pytest.raises(ValueError):
        slippage_bps(100, 100, "hold")


# --- aggregation --------------------------------------------------------------

def fill(bucket="first_hour", side="buy", dec=100.0, got=100.10, qty=10.0):
    return ExecutionFill(symbol="SPY", side=side, qty=qty, decision_price=dec,
                         fill_price=got, bucket=bucket, occurred_at="2026-08-14")


def test_empty_is_an_honest_answer_not_an_error():
    r = execution_report([])
    assert r.n_fills == 0 and r.avg_slippage_bps is None
    assert "no matched fills yet" in r.verdict and "sync.py" in r.verdict


def test_report_costs_and_buckets():
    fills = [fill(bucket="first_hour", got=100.20)] * 6 + \
            [fill(bucket="midday", got=100.00)] * 6
    r = execution_report(fills)
    assert r.n_fills == 12
    # 20bps on 1002 notional = $2.004 per fill, six of them
    assert r.by_bucket["first_hour"]["avg_bps"] == pytest.approx(20.0)
    assert r.by_bucket["midday"]["avg_bps"] == pytest.approx(0.0)
    assert r.avg_slippage_bps == pytest.approx(10.0)
    assert r.total_cost_dollars == pytest.approx(6 * 2.004, rel=1e-3)
    assert r.worst["slippage_bps"] == pytest.approx(20.0)
    assert "costing you" in r.verdict
    assert r.warnings == []                      # 6 >= MIN_BUCKET_SAMPLE


def test_thin_buckets_are_labeled_anecdote():
    r = execution_report([fill(bucket="pre", got=101.0)])
    assert r.by_bucket["pre"]["thin_sample"] is True
    assert any("anecdotes, not evidence" in w for w in r.warnings)
    assert MIN_BUCKET_SAMPLE == 5


def test_price_improvement_reads_negative():
    r = execution_report([fill(got=99.90)] * 5)
    assert r.avg_slippage_bps == pytest.approx(-10.0)
    assert "at or better than the decision price" in r.verdict
    assert r.total_cost_dollars < 0


def test_missing_bucket_groups_as_unknown():
    r = execution_report([fill(bucket=None)])
    assert "unknown" in r.by_bucket


# --- the tool joins signals to fills -----------------------------------------

def test_tool_matches_orders_to_fills_and_flags_unmatched():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with make_session_factory(engine)() as db:
        # two ordered signals; only one has a synced fill
        for oid, price, bucket in (("o1", 100.0, "first_hour"),
                                   ("o2", 200.0, "midday")):
            db.add(SignalLog(
                strategy="s", symbol="SPY", signal_weight=1.0, equity=1000.0,
                current_value=0.0, target_value=100.0, action="ordered",
                reasons=None, order_external_id=oid, bars_asof=now, source="t",
                ts=now - timedelta(days=1), entry_bucket=bucket,
                decision_price=price))
        db.add(Transaction(
            account_id=1, external_id="f1", symbol="SPY", side="buy", qty=10.0,
            price=100.30, occurred_at=now - timedelta(days=1), source="t",
            order_id="o1"))
        db.commit()
        out = registry.execute("get_execution_quality", {"days": 30},
                               ToolContext(db=db))
    assert out["n_fills"] == 1
    assert out["avg_slippage_bps"] == pytest.approx(30.0)   # 100.30 vs 100.00
    assert out["by_bucket"]["first_hour"]["n"] == 1
    assert any("no synced fill yet" in w for w in out["warnings"])
    assert out["source"] == "signal_log + transactions"
    engine.dispose()


def test_tool_empty_db_is_calm():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as db:
        out = registry.execute("get_execution_quality", {}, ToolContext(db=db))
    assert out["n_fills"] == 0 and "no matched fills yet" in out["verdict"]
    engine.dispose()
