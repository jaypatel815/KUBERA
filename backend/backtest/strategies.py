"""Strategy templates on the T030 contract: closes-so-far -> target weight [0..1]."""

from typing import Sequence

from analysis.metrics import sma


def buy_and_hold(closes: Sequence[float]) -> float:
    """Fully invested from the first decision onward."""
    return 1.0


def make_sma_cross(fast: int = 50, slow: int = 200):
    """Long when SMA(fast) > SMA(slow); flat otherwise (and while history is too short)."""
    if not 1 <= fast < slow:
        raise ValueError(f"need 1 <= fast < slow, got fast={fast} slow={slow}")

    def sma_cross(closes: Sequence[float]) -> float:
        if len(closes) < slow:
            return 0.0
        return 1.0 if sma(closes, fast) > sma(closes, slow) else 0.0

    sma_cross.__name__ = f"sma_cross_{fast}_{slow}"
    return sma_cross


def make_momentum(lookback: int = 60, threshold: float = 0.0):
    """Time-series momentum: long when the trailing `lookback`-bar return exceeds
    `threshold`; flat otherwise. The point of momentum is what it AVOIDS: it steps
    aside in sustained downtrends (verified by the bear-regime test)."""
    if lookback < 1:
        raise ValueError(f"lookback must be >= 1, got {lookback}")

    def momentum(closes: Sequence[float]) -> float:
        if len(closes) < lookback + 1:
            return 0.0
        trailing = closes[-1] / closes[-(lookback + 1)] - 1.0
        return 1.0 if trailing > threshold else 0.0

    momentum.__name__ = f"momentum_{lookback}"
    return momentum


def make_mean_reversion(window: int = 20, band_frac: float = 0.05):
    """Mean reversion: long while the close sits more than `band_frac` BELOW the
    SMA(window) — buying dips, flat otherwise. Stateless (no hysteresis): the position
    exits as soon as price re-enters the band. Suits choppy/range-bound regimes and
    deliberately stays out of steady trends (verified by regime tests)."""
    if window < 2:
        raise ValueError(f"window must be >= 2, got {window}")
    if not 0 < band_frac < 1:
        raise ValueError(f"band_frac must be in (0, 1), got {band_frac}")

    def mean_reversion(closes: Sequence[float]) -> float:
        if len(closes) < window:
            return 0.0
        return 1.0 if closes[-1] <= sma(closes, window) * (1.0 - band_frac) else 0.0

    mean_reversion.__name__ = f"mean_reversion_{window}"
    return mean_reversion
