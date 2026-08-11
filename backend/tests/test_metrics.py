"""Known-answer tests — every expected number below is hand-computed, not copied from
the implementation. If one fails, the METRIC is wrong, full stop (spec §9)."""

import pytest

from analysis.metrics import (
    cagr,
    cumulative_return,
    daily_returns,
    max_drawdown_frac,
    sharpe,
    volatility,
)

PRICES = [100.0, 110.0, 99.0, 108.9]  # +10%, -10%, +10% exactly
RETURNS = [0.10, -0.10, 0.10]


def test_daily_returns_exact():
    r = daily_returns(PRICES)
    assert r == pytest.approx(RETURNS)


def test_cumulative_return_exact():
    # 108.9 / 100 - 1 = 0.089
    assert cumulative_return(PRICES) == pytest.approx(0.089)


def test_cagr_two_years_ppy1():
    # 100 -> 121 over 2 periods at 1 period/year: sqrt(1.21) - 1 = 0.10 exactly
    assert cagr([100.0, 110.0, 121.0], periods_per_year=1) == pytest.approx(0.10)


def test_volatility_hand_computed_ppy1():
    # mean = 0.0333333; sample stdev = sqrt(0.02666667/2) = 0.11547005
    assert volatility(RETURNS, periods_per_year=1) == pytest.approx(0.11547005, abs=1e-8)


def test_volatility_annualizes_by_sqrt():
    v1 = volatility(RETURNS, periods_per_year=1)
    v252 = volatility(RETURNS, periods_per_year=252)
    assert v252 == pytest.approx(v1 * 252**0.5)


def test_sharpe_hand_computed_ppy1():
    # mean/stdev = 0.0333333 / 0.11547005 = 0.28867513
    assert sharpe(RETURNS, periods_per_year=1) == pytest.approx(0.28867513, abs=1e-8)


def test_sharpe_risk_free_reduces_ratio():
    assert sharpe(RETURNS, risk_free_rate=0.05) < sharpe(RETURNS, risk_free_rate=0.0)


def test_max_drawdown_hand_computed():
    # peak 120 -> trough 90 = 25% decline
    assert max_drawdown_frac([100.0, 120.0, 90.0, 130.0]) == pytest.approx(0.25)


def test_max_drawdown_monotonic_up_is_zero():
    assert max_drawdown_frac([100.0, 101.0, 102.0]) == 0.0


def test_max_drawdown_full_series_low_after_high():
    # peak 200 -> trough 50 = 75%, even with recovery after
    assert max_drawdown_frac([100.0, 200.0, 50.0, 199.0]) == pytest.approx(0.75)


@pytest.mark.parametrize("bad", [[], [100.0], [100.0, -5.0], [100.0, 0.0]])
def test_value_series_validation(bad):
    with pytest.raises(ValueError):
        daily_returns(bad)
    with pytest.raises(ValueError):
        max_drawdown_frac(bad)


def test_sharpe_zero_volatility_rejected():
    with pytest.raises(ValueError):
        sharpe([0.01, 0.01, 0.01])


def test_short_returns_rejected():
    with pytest.raises(ValueError):
        volatility([0.01])
