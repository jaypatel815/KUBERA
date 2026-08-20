"""T065b — the order-frequency rail: engine-level, persisted, sells exempt."""

import pytest
from test_paper_loop import db  # noqa: F401

from risk.engine import OrderRequest, RiskEngine, RiskLimits
from risk.persistence import persist_risk_state, restore_risk_state


def _engine(max_buys: int = 2) -> RiskEngine:
    e = RiskEngine(limits=RiskLimits(max_buys_per_day=max_buys))
    e.start_day(100_000.0, "2026-08-19")
    return e


def _buy(symbol: str = "SPY") -> OrderRequest:
    return OrderRequest(symbol=symbol, side="buy", qty=1.0, est_price=100.0)


def test_cap_refuses_with_named_reason_and_sells_stay_exempt():
    e = _engine(max_buys=2)
    assert e.pre_trade_check(_buy(), 100_000.0, 0.0).approved
    e.record_buy("2026-08-19")
    assert e.pre_trade_check(_buy(), 100_000.0, 0.0).approved   # 1 of 2
    e.record_buy("2026-08-19")

    d = e.pre_trade_check(_buy(), 100_000.0, 0.0)
    assert not d.approved
    assert any("order-frequency rail" in r and "2 buys" in r and "max 2" in r
               for r in d.reasons)

    sell = OrderRequest(symbol="SPY", side="sell", qty=1.0, est_price=100.0)
    assert e.pre_trade_check(sell, 100_000.0, 1000.0).approved  # never blocked


def test_count_rolls_over_with_the_market_day_no_job_needed():
    e = _engine(max_buys=1)
    e.record_buy("2026-08-19")
    assert not e.pre_trade_check(_buy(), 100_000.0, 0.0).approved
    e.start_day(100_000.0, "2026-08-20")            # next market day begins
    assert e.buys_today() == 0                      # stale count reads as 0
    assert e.pre_trade_check(_buy(), 100_000.0, 0.0).approved
    assert e.record_buy("2026-08-20") == 1          # counter restarted


def test_restart_cannot_forget_the_count(db):  # noqa: F811
    e = _engine(max_buys=2)
    e.record_buy("2026-08-19")
    e.record_buy("2026-08-19")
    persist_risk_state(db, e)

    fresh = RiskEngine(limits=RiskLimits(max_buys_per_day=2))
    assert restore_risk_state(db, fresh)
    assert fresh.buys_state == ("2026-08-19", 2)
    assert not fresh.pre_trade_check(_buy(), 100_000.0, 0.0).approved


def test_limit_validation_and_default():
    with pytest.raises(ValueError, match="max_buys_per_day"):
        RiskLimits(max_buys_per_day=0)
    with pytest.raises(ValueError, match="max_buys_per_day"):
        RiskLimits(max_buys_per_day=101)
    assert RiskLimits().max_buys_per_day == 5       # documented default


def test_restore_tolerates_legacy_rows_without_counts(db):  # noqa: F811
    e = _engine()
    persist_risk_state(db, e)                       # row with no buys recorded
    fresh = RiskEngine()
    assert restore_risk_state(db, fresh)
    assert fresh.buys_today("2026-08-19") == 0      # absent history is zero
    assert fresh.pre_trade_check(_buy(), 100_000.0, 0.0).approved
