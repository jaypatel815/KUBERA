"""Strategy library (T031): hand-tracked equity on tiny series + behavioral properties
across synthetic regimes (spec §9: every strategy proves itself in more than one market)."""

import pytest

from backtest.engine import run_backtest
from backtest.strategies import buy_and_hold, make_mean_reversion, make_momentum

# --- synthetic regimes (deterministic) --------------------------------------

BULL = [100.0 * (1.01**i) for i in range(120)]      # steady +1%/bar
BEAR = [100.0 * (0.99**i) for i in range(120)]      # steady -1%/bar
CHOP = [100.0 if i % 2 == 0 else 82.0 for i in range(120)]  # violent range
DATES = [f"d{i:03d}" for i in range(120)]


# --- momentum: hand-tracked -------------------------------------------------

def test_momentum_hand_tracked():
    closes = [100.0, 110.0, 99.0, 108.9, 120.0]
    dates = [f"d{i}" for i in range(5)]
    strat = make_momentum(lookback=1, threshold=0.0)
    r = run_backtest(closes, dates, strat, strat.__name__)
    # decisions: [100]->0 ; +10%->1 ; -10%->0 ; +10%->1
    assert r.weights == [0.0, 0.0, 1.0, 0.0, 1.0]
    assert r.equity_curve == pytest.approx([1.0, 1.0, 0.9, 0.9, 0.9 * 120.0 / 108.9])


# --- momentum: regime properties --------------------------------------------

def test_momentum_rides_the_bull():
    strat = make_momentum(lookback=10)
    r = run_backtest(BULL, DATES, strat, strat.__name__)
    # after warmup it is always long, and captures most of the trend
    assert all(w == 1.0 for w in r.weights[12:])
    assert r.cumulative_return > 1.5  # bull gains ~1.01**119; momentum misses only warmup


def test_momentum_steps_aside_in_the_bear():
    strat = make_momentum(lookback=10)
    r = run_backtest(BEAR, DATES, strat, strat.__name__)
    # trailing returns are always negative -> never invested -> capital preserved
    assert all(w == 0.0 for w in r.weights)
    assert r.cumulative_return == 0.0
    # and that beats buy-and-hold's loss by construction
    bh = run_backtest(BEAR, DATES, buy_and_hold, "bh")
    assert r.cumulative_return > bh.cumulative_return


# --- mean reversion: hand-tracked -------------------------------------------

def test_mean_reversion_hand_tracked():
    closes = [100.0, 100.0, 80.0, 100.0, 80.0, 100.0]
    dates = [f"d{i}" for i in range(6)]
    strat = make_mean_reversion(window=2, band_frac=0.05)
    r = run_backtest(closes, dates, strat, strat.__name__)
    # decisions (sma of last 2, band 5%):
    # [100]->0 ; [100,100] sma100 thr95, 100>95 ->0 ; [.,100,80] sma90 thr85.5, 80<=85.5 ->1 ;
    # [.,80,100] sma90, 100>85.5 ->0 ; [.,100,80] sma90, 80<=85.5 ->1
    assert r.weights == [0.0, 0.0, 0.0, 1.0, 0.0, 1.0]
    # rides: bar2->3 (+25%) and bar4->5 (+25%)
    assert r.equity_curve == pytest.approx([1.0, 1.0, 1.0, 1.25, 1.25, 1.5625])


# --- mean reversion: regime properties --------------------------------------

def test_mean_reversion_profits_in_chop():
    strat = make_mean_reversion(window=4, band_frac=0.05)
    r = run_backtest(CHOP, DATES, strat, strat.__name__)
    # buys the 82s inside a 100/82 range -> repeated +22% rides
    assert r.cumulative_return > 1.0


def test_mean_reversion_sits_out_a_steady_bull():
    strat = make_mean_reversion(window=4, band_frac=0.05)
    r = run_backtest(BULL, DATES, strat, strat.__name__)
    # price never dips 5% below its own short SMA in a smooth uptrend
    assert all(w == 0.0 for w in r.weights)
    assert r.cumulative_return == 0.0


# --- validation --------------------------------------------------------------

@pytest.mark.parametrize("bad_kwargs", [{"lookback": 0}])
def test_momentum_param_validation(bad_kwargs):
    with pytest.raises(ValueError):
        make_momentum(**bad_kwargs)


@pytest.mark.parametrize("bad_kwargs", [{"window": 1}, {"band_frac": 0.0}, {"band_frac": 1.0}])
def test_mean_reversion_param_validation(bad_kwargs):
    with pytest.raises(ValueError):
        make_mean_reversion(**bad_kwargs)
