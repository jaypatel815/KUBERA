"""Time-series metrics (T020) — pure, deterministic, strictly validated.

Conventions (every caller and every future strategy relies on these being stable):
- `values` are prices or equity levels, oldest first, all > 0.
- `returns` are per-period simple returns (0.10 == +10%), oldest first.
- `periods_per_year` defaults to 252 (US trading days).
- Annualization: volatility scales by sqrt(periods_per_year); Sharpe uses
  rf/periods_per_year as the per-period risk-free rate (simple approximation, documented).
- max_drawdown_frac returns a POSITIVE magnitude: 0.25 means a 25% peak-to-trough decline;
  0.0 means the series never fell below a prior peak.

Bad input raises ValueError — silent garbage in a money pipeline is never acceptable.
"""

from math import sqrt
from statistics import mean, stdev
from typing import Sequence

TRADING_DAYS = 252


def _check_values(values: Sequence[float], min_len: int = 2) -> None:
    if len(values) < min_len:
        raise ValueError(f"need at least {min_len} values, got {len(values)}")
    if any(v <= 0 for v in values):
        raise ValueError("all values must be > 0 (prices/equity levels)")


def daily_returns(values: Sequence[float]) -> list[float]:
    """Per-period simple returns between consecutive values."""
    _check_values(values)
    return [(values[i] / values[i - 1]) - 1.0 for i in range(1, len(values))]


def cumulative_return(values: Sequence[float]) -> float:
    """Total return over the whole series: last/first - 1."""
    _check_values(values)
    return values[-1] / values[0] - 1.0


def cagr(values: Sequence[float], periods_per_year: int = TRADING_DAYS) -> float:
    """Compound annual growth rate given one value per period."""
    _check_values(values)
    n_periods = len(values) - 1
    return (values[-1] / values[0]) ** (periods_per_year / n_periods) - 1.0


def volatility(
    returns: Sequence[float], periods_per_year: int = TRADING_DAYS
) -> float:
    """Annualized sample standard deviation of per-period returns."""
    if len(returns) < 2:
        raise ValueError(f"need at least 2 returns, got {len(returns)}")
    return stdev(returns) * sqrt(periods_per_year)


def sharpe(
    returns: Sequence[float],
    risk_free_rate: float = 0.0,
    periods_per_year: int = TRADING_DAYS,
) -> float:
    """Annualized Sharpe ratio. `risk_free_rate` is annual (e.g. 0.05 for 5%)."""
    if len(returns) < 2:
        raise ValueError(f"need at least 2 returns, got {len(returns)}")
    sd = stdev(returns)
    if sd == 0:
        raise ValueError("zero volatility — Sharpe undefined for a constant return series")
    rf_per_period = risk_free_rate / periods_per_year
    return (mean(returns) - rf_per_period) / sd * sqrt(periods_per_year)


def sma(values: Sequence[float], window: int) -> float:
    """Simple moving average of the LAST `window` values."""
    if window < 1:
        raise ValueError(f"window must be >= 1, got {window}")
    if len(values) < window:
        raise ValueError(f"need at least {window} values, got {len(values)}")
    tail = values[-window:]
    if any(v <= 0 for v in tail):
        raise ValueError("all values must be > 0 (prices/equity levels)")
    return sum(tail) / window


def true_ranges(
    highs: Sequence[float], lows: Sequence[float], closes: Sequence[float]
) -> list[float]:
    """True range per bar (Wilder): max(H-L, |H-prevC|, |L-prevC|). Returns n-1 values
    (the first bar has no previous close). Gaps are captured by the prev-close terms —
    close is deliberately NOT required to sit inside [low, high] (real feeds gap)."""
    n = len(closes)
    if not (len(highs) == len(lows) == n):
        raise ValueError("highs, lows, closes must be equal length")
    if n < 2:
        raise ValueError(f"need at least 2 bars, got {n}")
    for i in range(n):
        if highs[i] <= 0 or lows[i] <= 0 or closes[i] <= 0:
            raise ValueError(f"bar {i}: prices must be > 0")
        if lows[i] > highs[i]:
            raise ValueError(f"bar {i}: low {lows[i]} > high {highs[i]}")
    return [
        max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        for i in range(1, n)
    ]


def atr(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    window: int = 14,
) -> float:
    """Average True Range as of the LAST bar, Wilder's smoothing (the standard):
    seed = simple mean of the first `window` true ranges, then
    ATR_i = (ATR_{i-1} * (window-1) + TR_i) / window. Price units, not a fraction.
    Requires window+1 bars (one to anchor the first TR)."""
    if window < 1:
        raise ValueError(f"window must be >= 1, got {window}")
    trs = true_ranges(highs, lows, closes)
    if len(trs) < window:
        raise ValueError(f"need at least {window + 1} bars for ATR({window}), got {len(closes)}")
    value = sum(trs[:window]) / window
    for tr in trs[window:]:
        value = (value * (window - 1) + tr) / window
    return value


def max_drawdown_frac(values: Sequence[float]) -> float:
    """Largest peak-to-trough decline as a positive fraction (0.25 == fell 25%)."""
    _check_values(values)
    peak = values[0]
    worst = 0.0
    for v in values:
        peak = max(peak, v)
        worst = max(worst, 1.0 - v / peak)
    return worst
