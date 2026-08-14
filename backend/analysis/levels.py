"""Support/resistance estimation (T051) — "repeated rejections define the range".

From the owner's doctrine (docs/research/regime-trading-notes.md): a level is real
when price rejected it MORE THAN ONCE. So: find swing highs/lows (strict local
extrema, shared with the regime classifier), pool them, cluster by price proximity,
and keep only clusters with at least `min_touches` members. Each level reports its
touch count — the narration should weight a 5-touch level over a 2-touch one.

Definitions (stable contracts):
- Clustering: swings sorted by price, greedy walk — a swing joins the current
  cluster if its price <= cluster mean * (1 + tolerance_frac), else starts a new
  one. Deterministic, order-independent (sorted input), hand-computable.
- A cluster's price is the MEAN of its member swing prices.
- kind is provenance: "resistance" (all swing highs), "support" (all swing lows),
  or "mixed" (touched from both sides — e.g. old support acting as new resistance).
- nearest_support / nearest_resistance are POSITIONAL: the closest kept level
  strictly below / above the last close, regardless of provenance — the range
  playbook trades the nearest edges ("trade the edges, not the middle").
- distance_frac is signed: (level / last_close) - 1.

Pure deterministic code; bad input raises ValueError (fail closed).
"""

from dataclasses import dataclass
from typing import Sequence

from analysis.regime import swing_points


@dataclass(frozen=True)
class PriceLevel:
    price: float
    touches: int
    kind: str  # "support" | "resistance" | "mixed"
    first_date: str
    last_date: str
    distance_frac: float  # signed distance from last close


@dataclass(frozen=True)
class LevelsReading:
    as_of_date: str
    bars_used: int          # bars actually analyzed (after the lookback slice)
    last_close: float
    lookback_bars: int
    swing_span: int
    tolerance_frac: float
    min_touches: int
    swings_found: int       # raw swings before clustering/filtering
    levels: list[PriceLevel]  # kept levels, sorted by price ascending
    nearest_support: PriceLevel | None
    nearest_resistance: PriceLevel | None


def find_levels(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    dates: Sequence[str],
    *,
    lookback: int = 120,
    swing_span: int = 2,
    tolerance_frac: float = 0.01,
    min_touches: int = 2,
) -> LevelsReading:
    """Estimate support/resistance from the last `lookback` bars (or fewer if the
    series is shorter). Levels with fewer than `min_touches` swings are noise and
    are dropped — one rejection is an event, two is a level."""
    n = len(closes)
    if not (len(highs) == len(lows) == n == len(dates)):
        raise ValueError("highs, lows, closes, dates must be equal length")
    if swing_span < 1 or min_touches < 1:
        raise ValueError("swing_span and min_touches must be >= 1")
    if not 0 < tolerance_frac <= 0.2:
        raise ValueError(f"tolerance_frac must be in (0, 0.2], got {tolerance_frac}")
    min_bars = 2 * swing_span + 1
    if lookback < min_bars:
        raise ValueError(f"lookback must be >= {min_bars}, got {lookback}")
    if n < min_bars:
        raise ValueError(f"need at least {min_bars} bars, got {n}")
    for i in range(n):
        if highs[i] <= 0 or lows[i] <= 0 or closes[i] <= 0:
            raise ValueError(f"bar {i} ({dates[i]}): prices must be > 0")
        if lows[i] > highs[i]:
            raise ValueError(f"bar {i} ({dates[i]}): low {lows[i]} > high {highs[i]}")

    h, lo, d = highs[-lookback:], lows[-lookback:], dates[-lookback:]
    last_close = closes[-1]

    swings = [
        (p.price, p.date, "high") for p in swing_points(h, d, swing_span, "high")
    ] + [
        (p.price, p.date, "low") for p in swing_points(lo, d, swing_span, "low")
    ]
    swings.sort(key=lambda s: (s[0], s[1]))

    # greedy proximity clustering on the sorted swings
    clusters: list[list[tuple[float, str, str]]] = []
    mean = None
    for s in swings:
        if mean is not None and s[0] <= mean * (1 + tolerance_frac):
            clusters[-1].append(s)
            members = clusters[-1]
            mean = sum(m[0] for m in members) / len(members)
        else:
            clusters.append([s])
            mean = s[0]

    levels = []
    for members in clusters:
        if len(members) < min_touches:
            continue
        price = sum(m[0] for m in members) / len(members)
        kinds = {m[2] for m in members}
        kind = "mixed" if kinds == {"high", "low"} else (
            "resistance" if kinds == {"high"} else "support"
        )
        member_dates = [m[1] for m in members]
        levels.append(PriceLevel(
            price=price,
            touches=len(members),
            kind=kind,
            first_date=min(member_dates),
            last_date=max(member_dates),
            distance_frac=price / last_close - 1.0,
        ))
    levels.sort(key=lambda level: level.price)

    below = [level for level in levels if level.price < last_close]
    above = [level for level in levels if level.price > last_close]
    return LevelsReading(
        as_of_date=dates[-1],
        bars_used=len(h),
        last_close=last_close,
        lookback_bars=lookback,
        swing_span=swing_span,
        tolerance_frac=tolerance_frac,
        min_touches=min_touches,
        swings_found=len(swings),
        levels=levels,
        nearest_support=below[-1] if below else None,
        nearest_resistance=above[0] if above else None,
    )
