"""Strategy library (T031): hand-tracked equity on tiny series + behavioral properties
across synthetic regimes (spec §9: every strategy proves itself in more than one market)."""

import pytest

from backtest.engine import run_backtest
from backtest.strategies import (
    TEMPLATES,
    build_strategy,
    buy_and_hold,
    make_mean_reversion,
    make_momentum,
    make_range,
    make_regime_router,
)

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

# --- range strategy (T054): trade the edges, refuse the trends ---------------

def test_range_hand_tracked():
    # 8 flat bars, then a 100/82 alternation. Hand-walked prefix by prefix:
    # the strategy refuses while structure is UNKNOWN (early prefixes), refuses
    # while the SMA-slope fallback reads the first drop as "down" (L9, L11),
    # and only trades once two equal swing pairs prove a range (L13, L15).
    # Engine weights sit one bar after each decision (no-lookahead shift).
    closes = [100.0] * 8 + [82.0, 100.0, 82.0, 100.0, 82.0, 100.0, 82.0, 100.0]
    dates = [f"d{i}" for i in range(16)]
    strat = make_range(lookback=3)
    r = run_backtest(closes, dates, strat, strat.__name__)
    assert r.weights == [0.0] * 13 + [1.0, 0.0, 1.0]
    # two 82 -> 100 rides
    assert r.equity_curve[-1] == pytest.approx((100.0 / 82.0) ** 2)


def test_range_refuses_trending_structure():
    strat = make_range(lookback=40)
    for series in (BULL, BEAR):  # a "range" inside a trend is a trap — stand down
        r = run_backtest(series, DATES, strat, strat.__name__)
        assert all(w == 0.0 for w in r.weights)
        assert r.cumulative_return == 0.0


# --- regime router (T054): first decide what kind of market it is -------------

def test_router_rides_the_bull_via_momentum():
    strat = make_regime_router(lookback=40, momentum_lookback=10)
    r = run_backtest(BULL, DATES, strat, strat.__name__)
    assert all(w == 1.0 for w in r.weights[46:])  # structure detected -> momentum long
    assert r.cumulative_return > 1.0


def test_router_preserves_capital_in_the_bear():
    strat = make_regime_router(lookback=40, momentum_lookback=10)
    r = run_backtest(BEAR, DATES, strat, strat.__name__)
    assert all(w == 0.0 for w in r.weights)  # down structure -> momentum -> cash
    assert r.cumulative_return == 0.0


def test_router_beats_always_momentum_in_chop():
    # the T054 acceptance criterion, verbatim
    router = make_regime_router(lookback=40, momentum_lookback=60)
    mom = make_momentum(lookback=60)
    r_router = run_backtest(CHOP, DATES, router, router.__name__)
    r_mom = run_backtest(CHOP, DATES, mom, mom.__name__)
    assert r_mom.cumulative_return == 0.0   # 60-bar trailing return is 0 in 2-bar chop
    assert r_router.cumulative_return > 1.0  # range trading harvests the swings
    assert r_router.cumulative_return > r_mom.cumulative_return


def test_new_templates_buildable():
    assert callable(build_strategy("range")) and callable(build_strategy("regime_router"))
    assert set(TEMPLATES) >= {"range", "regime_router", "momentum", "mean_reversion"}


@pytest.mark.parametrize("bad_kwargs", [{"lookback": 1}, {"entry_frac": 0.0},
                                        {"entry_frac": 1.0}])
def test_range_param_validation(bad_kwargs):
    with pytest.raises(ValueError):
        make_range(**bad_kwargs)


@pytest.mark.parametrize("bad_kwargs", [{"lookback": 0}])
def test_momentum_param_validation(bad_kwargs):
    with pytest.raises(ValueError):
        make_momentum(**bad_kwargs)


@pytest.mark.parametrize("bad_kwargs", [{"window": 1}, {"band_frac": 0.0}, {"band_frac": 1.0}])
def test_mean_reversion_param_validation(bad_kwargs):
    with pytest.raises(ValueError):
        make_mean_reversion(**bad_kwargs)
