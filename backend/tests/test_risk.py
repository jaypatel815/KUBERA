"""Risk engine — the most exhaustively tested module in KUBERA (spec §9: a silent bug
here costs real money). Every number hand-computed; every rule tested from both sides."""

from datetime import datetime, timezone

import pytest

from risk.engine import OrderRequest, RiskEngine, RiskLimits

NOW = datetime(2026, 8, 11, 15, 0, 0, tzinfo=timezone.utc)


def engine(**limit_overrides) -> RiskEngine:
    e = RiskEngine(limits=RiskLimits(**limit_overrides))
    e.start_day(equity=100_000.0, day="2026-08-11")
    return e


def buy(qty=10, price=100.0, symbol="AAPL") -> OrderRequest:
    return OrderRequest(symbol=symbol, side="buy", qty=qty, est_price=price)


# --- limits validation -------------------------------------------------------

@pytest.mark.parametrize("bad", [{"max_position_frac": 0}, {"max_position_frac": 1.5},
                                 {"daily_loss_limit_frac": 0}, {"daily_loss_limit_frac": 1.0}])
def test_invalid_limits_rejected(bad):
    with pytest.raises(ValueError):
        RiskLimits(**bad)


# --- fail closed -------------------------------------------------------------

def test_uninitialized_engine_rejects_everything():
    e = RiskEngine()
    d = e.pre_trade_check(buy(), portfolio_equity=100_000.0, current_position_value=0.0)
    assert not d.approved
    assert any("start_day" in r for r in d.reasons)
    assert d.checked_at.tzinfo is not None


def test_record_equity_before_start_day_raises():
    with pytest.raises(ValueError):
        RiskEngine().record_equity(99_000.0, NOW)


# --- position cap (equity 100k, default cap 20% = 20k) ----------------------

def test_buy_within_cap_approved():
    # existing 10k + order 9k = 19k < 20k
    d = engine().pre_trade_check(buy(qty=90, price=100.0), 100_000.0, 10_000.0)
    assert d.approved and d.reasons == []


def test_buy_exactly_at_cap_approved():
    # existing 10k + order 10k = 20k == cap -> allowed (cap is inclusive)
    d = engine().pre_trade_check(buy(qty=100, price=100.0), 100_000.0, 10_000.0)
    assert d.approved


def test_buy_exceeding_cap_rejected_with_numbers():
    # existing 10k + order 11k = 21k > 20k
    d = engine().pre_trade_check(buy(qty=110, price=100.0), 100_000.0, 10_000.0)
    assert not d.approved
    assert len(d.reasons) == 1
    assert "21000.00" in d.reasons[0] and "20000.00" in d.reasons[0]


def test_sell_ignores_position_cap():
    sell = OrderRequest(symbol="AAPL", side="sell", qty=1000, est_price=100.0)
    d = engine().pre_trade_check(sell, 100_000.0, 90_000.0)  # way over cap, but reducing
    assert d.approved


@pytest.mark.parametrize("order", [
    OrderRequest("AAPL", "hold", 10, 100.0),
    OrderRequest("AAPL", "buy", 0, 100.0),
    OrderRequest("AAPL", "buy", 10, 0.0),
])
def test_malformed_orders_rejected(order):
    assert not engine().pre_trade_check(order, 100_000.0, 0.0).approved


def test_nonpositive_equity_rejected():
    assert not engine().pre_trade_check(buy(), 0.0, 0.0).approved


# --- circuit breaker (day start 100k, default limit 3%) ----------------------

def test_loss_below_limit_does_not_trip():
    e = engine()
    e.record_equity(97_100.0, NOW)  # -2.9%
    assert not e.tripped
    assert e.pre_trade_check(buy(), 97_100.0, 0.0).approved


def test_loss_at_limit_trips():
    e = engine()
    e.record_equity(97_000.0, NOW)  # exactly -3.0%
    assert e.tripped
    assert "3.00%" in (e.trip_reason or "")


def test_tripped_breaker_blocks_buys_and_sells():
    e = engine()
    e.record_equity(96_000.0, NOW)
    for side in ("buy", "sell"):
        d = e.pre_trade_check(
            OrderRequest("AAPL", side, 1, 100.0), 96_000.0, 10_000.0
        )
        assert not d.approved
        assert any("halted" in r for r in d.reasons)


def test_recovery_does_not_untrip():
    e = engine()
    e.record_equity(96_000.0, NOW)
    e.record_equity(105_000.0, NOW)  # roars back — breaker stays tripped
    assert e.tripped


def test_new_day_does_not_untrip():
    e = engine()
    e.record_equity(96_000.0, NOW)
    e.start_day(equity=96_000.0, day="2026-08-12")
    assert e.tripped
    assert not e.pre_trade_check(buy(), 96_000.0, 0.0).approved


def test_manual_reset_is_the_only_way_back():
    e = engine()
    e.record_equity(96_000.0, NOW)
    e.reset("owner reviewed the drawdown and re-enabled trading")
    assert not e.tripped
    assert e.pre_trade_check(buy(), 96_000.0, 0.0).approved


def test_multiple_violations_all_reported():
    e = engine()
    e.record_equity(96_000.0, NOW)  # tripped
    d = e.pre_trade_check(buy(qty=0), 96_000.0, 0.0)  # tripped AND qty invalid
    assert not d.approved
    assert len(d.reasons) == 2


def test_custom_limits_respected():
    e = engine(max_position_frac=0.10, daily_loss_limit_frac=0.05)
    # cap now 10k: existing 5k + 6k order = 11k > 10k
    assert not e.pre_trade_check(buy(qty=60, price=100.0), 100_000.0, 5_000.0).approved
    e.record_equity(95_500.0, NOW)  # -4.5% < 5% limit
    assert not e.tripped
    e.record_equity(95_000.0, NOW)  # -5.0% -> trip
    assert e.tripped
