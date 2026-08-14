"""Strategy templates on the T030 contract: closes-so-far -> target weight [0..1].

T054 adds the doctrine pair: a range trader that only trades the edges of a
range-bound market (and refuses trends), and a regime router that picks
momentum / range / CASH from the price structure. NOTE the honest limitation:
the T030 contract is closes-only (D010), so in-backtest regime detection is
price-structure only (`_regime_lite`) — no volume. The LIVE paper loop has full
OHLCV and layers the volume-aware no-trade checks on top (T055)."""

from typing import Callable, Sequence

from analysis.metrics import sma
from analysis.regime import swing_points


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


# Shared template registry: one place both the CLI and the API/tools build from.
TEMPLATES: dict[str, Callable[[], Callable[[Sequence[float]], float]]] = {
    "buy_and_hold": lambda: buy_and_hold,
    "momentum": lambda: make_momentum(lookback=60),
    "sma_cross": lambda: make_sma_cross(fast=50, slow=200),
    "mean_reversion": lambda: make_mean_reversion(window=20, band_frac=0.05),
    "range": lambda: make_range(lookback=40),
    "regime_router": lambda: make_regime_router(lookback=40, momentum_lookback=60),
}


def build_strategy(name: str):
    """Instantiate a template by name; ValueError lists valid names."""
    if name not in TEMPLATES:
        raise ValueError(f"unknown strategy '{name}' — valid: {', '.join(sorted(TEMPLATES))}")
    return TEMPLATES[name]()


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


def _regime_lite(closes: Sequence[float], lookback: int, span: int = 1) -> str:
    """Price-only trend structure: 'up' | 'down' | 'none' | 'unknown'. Mirrors the
    T050 classifier's structure logic (swing HH/HL, SMA-slope fallback for monotone
    series) but from closes alone — the T030 contract carries no volume, so this is
    deliberately structure-only. span=1 so short-period chop still forms swings.
    'none' means CHECKED and rangy; 'unknown' means not enough evidence to judge —
    callers that require a range must refuse on 'unknown' (an early bear looks
    exactly like an unknowable one until the structure resolves)."""
    window = closes[-min(len(closes), 4 * lookback):]
    dates = [str(i) for i in range(len(window))]
    highs = swing_points(window, dates, span, "high")
    lows = swing_points(window, dates, span, "low")
    if len(highs) >= 2 and len(lows) >= 2:
        if highs[-1].price > highs[-2].price and lows[-1].price > lows[-2].price:
            return "up"
        if highs[-1].price < highs[-2].price and lows[-1].price < lows[-2].price:
            return "down"
        return "none"
    if len(closes) >= lookback + 5:
        sma_now, sma_prev = sma(closes, lookback), sma(closes[:-5], lookback)
        if sma_now > sma_prev and closes[-1] > sma_now:
            return "up"
        if sma_now < sma_prev and closes[-1] < sma_now:
            return "down"
        return "none"
    return "unknown"


def make_range(lookback: int = 40, entry_frac: float = 0.5):
    """Range trading, doctrine-faithful: trade the edges, never the middle, and
    ONLY in a range. Long while the close sits in the lower `entry_frac` of the
    trailing `lookback`-bar range; flat in the upper part; and REFUSES to trade
    at all when the price structure is trending ('a range detected inside a
    downtrend is a falling knife'). Stateless on the closes prefix."""
    if lookback < 2:
        raise ValueError(f"lookback must be >= 2, got {lookback}")
    if not 0 < entry_frac < 1:
        raise ValueError(f"entry_frac must be in (0, 1), got {entry_frac}")

    def range_trader(closes: Sequence[float]) -> float:
        if len(closes) < lookback:
            return 0.0
        if _regime_lite(closes, lookback) != "none":
            return 0.0  # trending OR unverifiable structure: not a range — stand down
        window = closes[-lookback:]
        lo, hi = min(window), max(window)
        if hi <= lo:
            return 0.0  # degenerate (zero-width) range: nothing to trade
        pos = (closes[-1] - lo) / (hi - lo)
        return 1.0 if pos <= entry_frac else 0.0

    range_trader.__name__ = f"range_{lookback}"
    return range_trader


def make_regime_router(lookback: int = 40, momentum_lookback: int = 60,
                       entry_frac: float = 0.5):
    """The meta-strategy (T054): first determine what kind of market it is, then
    pick the playbook — trending structure -> momentum (which itself goes to cash
    in downtrends), no structure -> range trading (which refuses non-ranges).
    CASH emerges whenever the chosen playbook declines; that is a feature."""
    mom = make_momentum(lookback=momentum_lookback)
    rng = make_range(lookback=lookback, entry_frac=entry_frac)

    def regime_router(closes: Sequence[float]) -> float:
        if _regime_lite(closes, lookback) in ("up", "down"):
            regime_router.last_leg = "momentum"  # T091: which leg fired (introspection)
            return mom(closes)
        regime_router.last_leg = "range"
        return rng(closes)

    regime_router.last_leg = None

    regime_router.__name__ = f"regime_router_{lookback}_{momentum_lookback}"
    return regime_router
