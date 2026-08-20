"""T064b-rest — crisis-window stress runs: slicing honesty + the comparator."""

import pytest

from backtest.stress import (
    IMPOSSIBLE_WINDOWS,
    MIN_WINDOW_BARS,
    WINDOWS,
    CoverageError,
    StressWindow,
    slice_window,
    stress_template,
)

W = StressWindow("test-crash", "2020-01-02", "2020-06-30", "fixture")


def _series(start="2019-01-02", n=650):
    """Business-day-ish ISO dates (every day; weekends don't matter to the
    slicer) with a rise -> crash -> flat shape around the window."""
    from datetime import date, timedelta
    d0 = date.fromisoformat(start)
    dates = [(d0 + timedelta(days=i)).isoformat() for i in range(n)]
    closes = []
    px = 100.0
    for i, day in enumerate(dates):
        if day < "2020-02-15":
            px *= 1.001          # calm rise into the window
        elif day < "2020-03-25":
            px *= 0.98           # the crash: ~40 sessions of -2%
        else:
            px *= 1.0005         # slow stabilization
        closes.append(px)
    return dates, closes


def test_slice_is_inclusive_and_exact():
    dates, closes = _series()
    wd, wc = slice_window(dates, closes, W)
    assert wd[0] == "2020-01-02" and wd[-1] == "2020-06-30"
    assert len(wd) == len(wc) and len(wd) >= MIN_WINDOW_BARS
    # exact positional integrity: the slice IS the original data, re-indexed
    assert wc[0] == closes[dates.index("2020-01-02")]


def test_coverage_refusals_are_named():
    dates, closes = _series()
    late = StressWindow("late-start", "2018-01-01", "2020-06-30", "f")
    with pytest.raises(CoverageError, match="after the window opens"):
        slice_window(dates, closes, late)            # feed starts 2019
    truncated = StressWindow("cut-end", "2020-01-02", "2099-01-01", "f")
    with pytest.raises(CoverageError, match="before the window closes"):
        slice_window(dates, closes, truncated)
    nothing = StressWindow("void", "1990-01-01", "1990-06-30", "f")
    with pytest.raises(CoverageError, match="no bars inside"):
        slice_window(dates, closes, nothing)


def test_stress_report_momentum_protects_vs_buy_and_hold():
    dates, closes = _series()
    rep = stress_template("momentum", "spy", dates, closes, W, cost_bps=5.0)
    assert rep.symbol == "SPY" and rep.window == "test-crash"
    # at ZERO cost, buy-and-hold is pure arithmetic on the window slice
    # (at 5 bps the engine's entry cost is in the number — by design):
    rep0 = stress_template("momentum", "SPY", dates, closes, W, cost_bps=0.0)
    wd, wc = slice_window(dates, closes, W)
    assert rep0.buy_and_hold.cumulative_return == pytest.approx(
        wc[-1] / wc[0] - 1.0, rel=1e-9)
    assert rep.buy_and_hold.cumulative_return < \
        rep0.buy_and_hold.cumulative_return          # costs only ever hurt
    # momentum goes flat once the trailing return turns negative — its
    # drawdown must be smaller than holding through the crash:
    assert rep.strategy.max_drawdown_frac < rep.buy_and_hold.max_drawdown_frac
    assert rep.drawdown_saved_frac > 0
    # T109b: the 2x-cost run can never be BETTER than the base run
    assert rep.strategy_2x_cost.cumulative_return <= \
        rep.strategy.cumulative_return + 1e-12
    assert "recorded nowhere" in rep.note


def test_named_windows_and_the_impossible_one():
    names = [w.name for w in WINDOWS]
    assert names == ["covid-2020", "bear-2022"]
    assert all(w.start < w.end for w in WINDOWS)
    imp = dict(IMPOSSIBLE_WINDOWS)
    assert "gfc-2008" in imp and "IEX" in imp["gfc-2008"]


def test_unknown_template_refused():
    dates, closes = _series()
    with pytest.raises(ValueError, match="unknown strategy"):
        stress_template("nope", "SPY", dates, closes, W)
