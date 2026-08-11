"""Backtest engine — every expected number hand-computed (D010: the engine is money math)."""

import pytest

from backtest.engine import run_backtest
from backtest.strategies import buy_and_hold, make_sma_cross

PRICES = [100.0, 110.0, 99.0, 108.9]  # returns +10%, -10%, +10%
DATES = ["2026-08-01", "2026-08-02", "2026-08-03", "2026-08-04"]


def test_buy_and_hold_hand_computed():
    r = run_backtest(PRICES, DATES, buy_and_hold, "bh")
    assert r.equity_curve == pytest.approx([1.0, 1.10, 0.99, 1.089])
    assert r.cumulative_return == pytest.approx(0.089)
    assert r.max_drawdown_frac == pytest.approx(0.10)  # 1.10 -> 0.99
    assert r.n_rebalances == 1  # single 0 -> 1 shift
    assert r.total_cost_frac == 0.0
    assert r.weights == [0.0, 1.0, 1.0, 1.0]


def test_transaction_cost_hand_computed():
    # 100 bps: shifting 0->1 at equity 1.0 costs 0.01
    r = run_backtest(PRICES, DATES, buy_and_hold, "bh", cost_bps=100)
    assert r.equity_curve[0] == 1.0
    assert r.equity_curve[1] == pytest.approx(0.99 * 1.10)
    assert r.equity_curve[-1] == pytest.approx(0.99 * 1.10 * 0.90 * 1.10)
    assert r.total_cost_frac == pytest.approx(0.01)


def test_engine_enforces_no_lookahead():
    """The strategy must only ever see the prefix up to 'today'."""
    seen = []

    def spy(closes):
        seen.append(len(closes))
        return 0.0

    run_backtest(PRICES, DATES, spy, "spy")
    assert seen == [1, 2, 3]  # never the full 4-bar series on decision day


def test_never_invested_is_flat_with_undefined_sharpe():
    r = run_backtest(PRICES, DATES, lambda closes: 0.0, "flat")
    assert r.equity_curve == pytest.approx([1.0, 1.0, 1.0, 1.0])
    assert r.cumulative_return == 0.0
    assert r.max_drawdown_frac == 0.0
    assert r.sharpe_ann is None  # zero volatility -> undefined, not fake


def test_sma_cross_hand_tracked():
    closes = [10.0, 20.0, 10.0, 20.0, 30.0]
    dates = [f"2026-08-0{i}" for i in range(1, 6)]
    strat = make_sma_cross(fast=1, slow=2)
    r = run_backtest(closes, dates, strat, strat.__name__)
    # decisions: [10]->0 ; [10,20]->1 ; [10,20,10]->0 ; [10,20,10,20]->1
    # rides:      +100%(w0)  -50%(w1)    +100%(w0)      +50%(w1)
    assert r.weights == [0.0, 0.0, 1.0, 0.0, 1.0]
    assert r.equity_curve == pytest.approx([1.0, 1.0, 0.5, 0.5, 0.75])
    assert r.n_rebalances == 3


def test_invalid_strategy_weight_rejected():
    with pytest.raises(ValueError) as exc:
        run_backtest(PRICES, DATES, lambda closes: 1.5, "bad")
    assert "must be within [0, 1]" in str(exc.value)


def test_sma_cross_param_validation():
    with pytest.raises(ValueError):
        make_sma_cross(fast=200, slow=50)


@pytest.mark.parametrize(
    "closes,dates,kwargs",
    [
        ([100.0], ["d1"], {}),                                  # too short
        ([100.0, -1.0], ["d1", "d2"], {}),                      # nonpositive close
        ([100.0, 110.0], ["d1"], {}),                           # length mismatch
        (PRICES, DATES, {"cost_bps": 10_000}),                  # cost out of range
    ],
)
def test_malformed_input_rejected(closes, dates, kwargs):
    with pytest.raises(ValueError):
        run_backtest(closes, dates, buy_and_hold, "bh", **kwargs)
