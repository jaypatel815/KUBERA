"""Regime classifier (T050) — "first determine what kind of day it is".

Implements the owner's doctrine (docs/research/regime-trading-notes.md) on DAILY bars:
classify one of trending_up / trending_down / range_bound / breakout_watch and return
every underlying number so the conversation layer narrates evidence, not vibes.
Intraday VWAP/RVOL arrive with T052; the breakout refinement is T053.

Definitions (stable contracts — tests and later tickets rely on these):
- Inputs are equal-length sequences, oldest first: highs, lows, closes, volumes, dates.
  `volume_feed` is REQUIRED (D006): every volume statement must name its feed.
- Standing range  = last `range_lookback` bars (incl. the last): max(high)..min(low).
  Width is quoted as a fraction of the range midpoint (scale-invariant).
- Escape         = last close strictly outside the extremes of the PRIOR
  `range_lookback` bars (excluding the last bar).
- Width percentile = share of all OTHER complete rolling windows (over the full series
  provided) whose width-fraction is <= the current window's. Low = unusually narrow
  (the coil). None when fewer than 10 other windows exist.
- RVOL           = last volume / mean volume of the prior `rvol_baseline` bars.
  Relative to this symbol's own history on the same feed — valid as a relative
  measure on IEX; absolute claims need SIP (D006). None if the baseline mean is 0.
- Swing high/low = bar strictly above/below every bar within `swing_span` on both
  sides, searched over the last 4*range_lookback bars. Structure "up" needs BOTH a
  higher swing high and a higher swing low (doctrine: higher highs AND higher lows);
  "down" is the mirror; ties or mixes = "none". When fewer than 2 swings exist per
  side (e.g. a monotone series has no swings), fall back to SMA slope: SMA rising
  over 5 bars with close above it = "up" (method is reported either way).

Decision order (first match wins — a matured trend outranks its own escapes):
1. structure up  and close > SMA(range_lookback)  -> trending_up
2. structure down and close < SMA(range_lookback) -> trending_down
3. escaped up or down                             -> breakout_watch
   (suspected_fakeout=True when RVOL < 1.0 — the $100->$106->$99 lesson)
4. width percentile <= 0.25                       -> breakout_watch (the coil)
5. otherwise                                      -> range_bound

Confidence = 0.35 + 0.15 * (passing checks from the label's fixed 3-signal checklist),
capped at 0.9 — a daily-bar heuristic never gets to claim certainty. The checklist
booleans are returned in `checks` so narration can say WHY confidence is what it is.

Bad input raises ValueError — silent garbage in a money pipeline is never acceptable.
"""

from dataclasses import dataclass
from statistics import mean
from typing import Sequence

from analysis.metrics import sma

TRENDING_UP = "trending_up"
TRENDING_DOWN = "trending_down"
RANGE_BOUND = "range_bound"
BREAKOUT_WATCH = "breakout_watch"

COIL_PERCENTILE = 0.25      # width percentile at/below which the range counts as "tight"
RVOL_CONFIRM = 1.25         # RVOL at/above which volume "confirms" a move
RVOL_FAKEOUT = 1.0          # an escape below this RVOL is a suspected fakeout
MIN_PERCENTILE_WINDOWS = 10  # fewer other windows than this -> percentile is None
_REL_TOL = 1e-9


@dataclass(frozen=True)
class SwingPoint:
    date: str
    price: float


@dataclass(frozen=True)
class RegimeReading:
    regime: str
    confidence: float
    reason: str
    as_of_date: str
    bars_used: int
    # trend structure
    structure: str            # "up" | "down" | "none"
    structure_method: str     # "swings" | "sma_slope" | "insufficient"
    swing_highs: list[SwingPoint]  # the (up to 2) most recent swing highs used
    swing_lows: list[SwingPoint]
    # levels
    last_close: float
    sma: float
    range_lookback: int
    range_high: float
    range_low: float
    range_width_frac: float
    range_width_percentile: float | None
    close_position_in_range: float | None  # 0=at range low, 1=at range high
    # escape / breakout evidence
    escaped_up: bool
    escaped_down: bool
    suspected_fakeout: bool
    # volume (D006: always labeled)
    rvol: float | None
    rvol_baseline_days: int
    volume_feed: str
    volume_note: str
    # confidence evidence
    checks: dict[str, bool]


def _validate(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
    dates: Sequence[str],
    min_bars: int,
    volume_feed: str,
) -> None:
    n = len(closes)
    if not (len(highs) == len(lows) == n == len(volumes) == len(dates)):
        raise ValueError("highs, lows, closes, volumes, dates must be equal length")
    if n < min_bars:
        raise ValueError(f"need at least {min_bars} bars for these lookbacks, got {n}")
    if not volume_feed.strip():
        raise ValueError("volume_feed is required (D006: label every volume statement)")
    for i in range(n):
        h, lo, c, v = highs[i], lows[i], closes[i], volumes[i]
        if lo <= 0 or c <= 0 or h <= 0:
            raise ValueError(f"bar {i} ({dates[i]}): prices must be > 0")
        if lo > h:
            raise ValueError(f"bar {i} ({dates[i]}): low {lo} > high {h}")
        if c > h * (1 + 1e-6) or c < lo * (1 - 1e-6):
            raise ValueError(f"bar {i} ({dates[i]}): close {c} outside [{lo}, {h}]")
        if v < 0:
            raise ValueError(f"bar {i} ({dates[i]}): volume must be >= 0")


def _window_width_frac(highs: Sequence[float], lows: Sequence[float]) -> float:
    hi, lo = max(highs), min(lows)
    mid = (hi + lo) / 2.0
    return (hi - lo) / mid


def _width_percentile(
    highs: Sequence[float], lows: Sequence[float], lookback: int
) -> float | None:
    n = len(highs)
    widths = [
        _window_width_frac(highs[e - lookback + 1: e + 1], lows[e - lookback + 1: e + 1])
        for e in range(lookback - 1, n)
    ]
    current, others = widths[-1], widths[:-1]
    if len(others) < MIN_PERCENTILE_WINDOWS:
        return None
    tol = _REL_TOL * max(1.0, abs(current))
    return sum(1 for w in others if w <= current + tol) / len(others)


def _swing_points(
    values: Sequence[float], dates: Sequence[str], span: int, kind: str
) -> list[SwingPoint]:
    """Strict local extrema: above/below EVERY bar within `span` on both sides."""
    out = []
    for i in range(span, len(values) - span):
        neighbors = [values[j] for j in range(i - span, i + span + 1) if j != i]
        if kind == "high" and all(values[i] > x for x in neighbors):
            out.append(SwingPoint(dates[i], values[i]))
        elif kind == "low" and all(values[i] < x for x in neighbors):
            out.append(SwingPoint(dates[i], values[i]))
    return out


def _structure(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    dates: Sequence[str],
    range_lookback: int,
    swing_span: int,
) -> tuple[str, str, list[SwingPoint], list[SwingPoint]]:
    window = min(len(closes), 4 * range_lookback)
    h, lo, d = highs[-window:], lows[-window:], dates[-window:]
    swing_highs = _swing_points(h, d, swing_span, "high")
    swing_lows = _swing_points(lo, d, swing_span, "low")

    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        sh, sl = swing_highs[-2:], swing_lows[-2:]
        if sh[1].price > sh[0].price and sl[1].price > sl[0].price:
            return "up", "swings", sh, sl
        if sh[1].price < sh[0].price and sl[1].price < sl[0].price:
            return "down", "swings", sh, sl
        return "none", "swings", sh, sl

    # monotone/thin series produce no swings — fall back to SMA slope over 5 bars
    if len(closes) >= range_lookback + 5:
        sma_now = sma(closes, range_lookback)
        sma_prev = sma(closes[:-5], range_lookback)
        last = closes[-1]
        if sma_now > sma_prev and last > sma_now:
            return "up", "sma_slope", swing_highs[-2:], swing_lows[-2:]
        if sma_now < sma_prev and last < sma_now:
            return "down", "sma_slope", swing_highs[-2:], swing_lows[-2:]
        return "none", "sma_slope", swing_highs[-2:], swing_lows[-2:]
    return "none", "insufficient", swing_highs[-2:], swing_lows[-2:]


def classify_regime(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
    dates: Sequence[str],
    *,
    volume_feed: str,
    range_lookback: int = 20,
    rvol_baseline: int = 20,
    swing_span: int = 2,
) -> RegimeReading:
    """Classify the regime as of the LAST bar. Pass ~120+ bars for a meaningful
    width percentile; with less history the percentile (and the coil rule) degrade
    to None/inactive rather than guessing."""
    if range_lookback < 2 or rvol_baseline < 1 or swing_span < 1:
        raise ValueError("range_lookback >= 2, rvol_baseline >= 1, swing_span >= 1")
    min_bars = max(range_lookback, rvol_baseline) + 1
    _validate(highs, lows, closes, volumes, dates, min_bars, volume_feed)
    n = len(closes)
    last = closes[-1]

    # levels
    range_high = max(highs[-range_lookback:])
    range_low = min(lows[-range_lookback:])
    width_frac = _window_width_frac(highs[-range_lookback:], lows[-range_lookback:])
    width_pct = _width_percentile(highs, lows, range_lookback)
    span_px = range_high - range_low
    close_pos = None
    if span_px > 0:
        close_pos = min(1.0, max(0.0, (last - range_low) / span_px))

    # escape vs the prior window (excluding the last bar)
    prior_high = max(highs[-range_lookback - 1: -1])
    prior_low = min(lows[-range_lookback - 1: -1])
    escaped_up = last > prior_high
    escaped_down = last < prior_low

    # volume
    baseline = volumes[-rvol_baseline - 1: -1]
    base_mean = mean(baseline)
    rvol = (volumes[-1] / base_mean) if base_mean > 0 else None

    # trend structure
    structure, method, swing_highs, swing_lows = _structure(
        highs, lows, closes, dates, range_lookback, swing_span
    )
    sma_val = sma(closes, range_lookback)

    escaped = escaped_up or escaped_down
    suspected_fakeout = escaped and rvol is not None and rvol < RVOL_FAKEOUT

    # decision (documented order — first match wins)
    if structure == "up" and last > sma_val:
        regime = TRENDING_UP
        reason = (
            f"higher highs and higher lows ({method}) with the close above the "
            f"{range_lookback}-bar average"
        )
    elif structure == "down" and last < sma_val:
        regime = TRENDING_DOWN
        reason = (
            f"lower highs and lower lows ({method}) with the close below the "
            f"{range_lookback}-bar average"
        )
    elif escaped:
        direction = "above" if escaped_up else "below"
        confirmed = rvol is not None and rvol >= RVOL_CONFIRM
        reason = (
            f"close escaped {direction} the prior {range_lookback}-bar range "
            + ("with volume confirmation"
               if confirmed else "WITHOUT volume confirmation — treat with suspicion")
        )
        regime = BREAKOUT_WATCH
    elif width_pct is not None and width_pct <= COIL_PERCENTILE:
        regime = BREAKOUT_WATCH
        reason = (
            f"range width in the {width_pct:.0%} percentile of trailing history — "
            "coiled; watch for a volume-confirmed expansion"
        )
    else:
        regime = RANGE_BOUND
        reason = "no directional swing structure; price oscillating inside its range"

    # confidence checklist (3 fixed signals per label)
    if regime in (TRENDING_UP, TRENDING_DOWN):
        checks = {
            "structure_from_swings": method == "swings",
            "volume_participation": rvol is not None and rvol >= 1.0,
            "range_expanding": width_pct is not None and width_pct >= 0.5,
        }
    elif regime == BREAKOUT_WATCH:
        checks = {
            "escaped": escaped,
            "volume_confirmed": rvol is not None and rvol >= RVOL_CONFIRM,
            "tight_range": width_pct is not None and width_pct <= COIL_PERCENTILE,
        }
    else:
        checks = {
            "structure_none": structure == "none",
            "mid_range_close": close_pos is not None and 0.2 <= close_pos <= 0.8,
            "quiet_volume": rvol is not None and rvol <= RVOL_CONFIRM,
        }
    confidence = min(0.9, 0.35 + 0.15 * sum(checks.values()))

    return RegimeReading(
        regime=regime,
        confidence=confidence,
        reason=reason,
        as_of_date=dates[-1],
        bars_used=n,
        structure=structure,
        structure_method=method,
        swing_highs=swing_highs,
        swing_lows=swing_lows,
        last_close=last,
        sma=sma_val,
        range_lookback=range_lookback,
        range_high=range_high,
        range_low=range_low,
        range_width_frac=width_frac,
        range_width_percentile=width_pct,
        close_position_in_range=close_pos,
        escaped_up=escaped_up,
        escaped_down=escaped_down,
        suspected_fakeout=suspected_fakeout,
        rvol=rvol,
        rvol_baseline_days=rvol_baseline,
        volume_feed=volume_feed,
        volume_note=(
            f"RVOL is relative to this symbol's own history on the same feed "
            f"({volume_feed}); relative comparisons are valid, but absolute volume "
            "claims require the consolidated SIP feed (D006)."
        ),
        checks=checks,
    )
