"""Expected-move & payoff distribution engine (T077, D016/D017).

KUBERA never forecasts a price point. What it CAN say honestly: "over the last
year, this symbol's 5-day moves landed between −2.1% and +2.4% ninety percent of
the time; 54% of those windows were up; winners averaged 1.8x the losers." That
is a distribution of the PAST — an anchor for sizing and exits, not a prediction.

Definitions (stable contracts):
- Samples are OVERLAPPING horizon-day simple returns closes[i+h]/closes[i]-1 over
  the trailing `lookback` window. Overlap autocorrelates samples and understates
  tail independence — stated in every reading's note.
- Percentiles p05/p25/p50/p75/p95 use inclusive linear interpolation
  (statistics.quantiles(method="inclusive") — hand-computable).
- up_frac      = share of samples > 0 (historical "long-and-hold-h-days" win rate)
- expected_abs_move_frac = median |sample| — the typical magnitude, either way
- payoff_ratio = mean gain of up-samples / mean |loss| of down-samples; None when
  a side is empty.
- Vol clustering: volatility begets volatility, so bands are ALSO conditioned on
  the current trailing-vol tercile — each sample is bucketed by the stdev of the
  `vol_window` daily returns ending at its start; the reading reports which
  tercile "now" is in and the bands from matching history (None under
  `min_samples`). Quiet tape -> narrower honest bands; wild tape -> wider.

Bad input raises ValueError — fail closed.
"""

import random
from dataclasses import dataclass
from statistics import mean, median, quantiles, stdev
from typing import Sequence

PCT_KEYS = ("p05", "p25", "p50", "p75", "p95")
_PCT_INDEX = {"p05": 4, "p25": 24, "p50": 49, "p75": 74, "p95": 94}

# T077b: default seed for bootstrap bands. A CONSTANT, deliberately (D017):
# the same bars in must produce the same bands out, today and in a re-audit
# next month. Callers wanting a different draw pass their own seed — and the
# seed used is always reported in the payload.
DEFAULT_BOOTSTRAP_SEED = 7


@dataclass(frozen=True)
class ReturnBands:
    samples: int
    percentiles: dict[str, float]   # horizon-day simple returns
    band_prices: dict[str, float]   # the same bands mapped onto price from last close
    up_frac: float
    expected_abs_move_frac: float
    payoff_ratio: float | None


@dataclass(frozen=True)
class ExpectedMoveReading:
    horizon_days: int
    lookback_days: int
    vol_window: int
    as_of_date: str
    last_close: float
    unconditional: ReturnBands
    current_vol_tercile: str | None   # "low" | "mid" | "high"; None if history is thin
    conditioned: ReturnBands | None   # bands from same-tercile history only
    note: str


def _bands(samples: Sequence[float], last_close: float) -> ReturnBands:
    qs = quantiles(samples, n=100, method="inclusive")
    pct = {k: qs[i] for k, i in _PCT_INDEX.items()}
    gains = [s for s in samples if s > 0]
    losses = [-s for s in samples if s < 0]
    payoff = (mean(gains) / mean(losses)) if gains and losses else None
    return ReturnBands(
        samples=len(samples),
        percentiles=pct,
        band_prices={k: last_close * (1.0 + v) for k, v in pct.items()},
        up_frac=len(gains) / len(samples),
        expected_abs_move_frac=median(abs(s) for s in samples),
        payoff_ratio=payoff,
    )


@dataclass(frozen=True)
class BootstrapBands:
    """Percentile bands of block-bootstrapped horizon returns (T077b, D017)."""

    n_paths: int
    block_days: int
    seed: int
    horizon_days: int
    history_days: int               # daily returns actually resampled from
    percentiles: dict[str, float]   # horizon-return fractions
    band_prices: dict[str, float]
    up_frac: float
    note: str


def bootstrap_paths(
    closes: Sequence[float],
    *,
    horizon_days: int = 5,
    lookback: int = 252,
    n_paths: int = 1000,
    block_days: int = 5,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
    min_history: int = 60,
) -> BootstrapBands:
    """Block-bootstrap Monte Carlo bands for horizon-day returns.

    Complements `expected_move`'s overlapping-window estimator: instead of
    reading the h-day windows history happened to produce, this RESAMPLES the
    trailing daily returns into `n_paths` synthetic h-day paths and reads the
    percentiles of their terminal returns. Blocks of `block_days` contiguous
    returns are drawn (with replacement) rather than single days, because
    volatility clusters — iid resampling would shuffle calm and wild days
    together and understate both tails.

    DETERMINISTIC GIVEN SEED (D017): random.Random(seed), no global state; the
    same closes and parameters always produce identical bands, so a reading
    can be re-audited later. The seed rides along in the result.

    Honesty limits, stated in the note: paths are recombinations of the PAST —
    the bootstrap cannot produce a regime history never contained, and block
    joins break correlations longer than `block_days`.
    """
    if horizon_days < 1 or lookback < 2 or block_days < 1:
        raise ValueError("horizon_days >= 1, lookback >= 2, block_days >= 1")
    if n_paths < 100:
        raise ValueError(f"n_paths must be >= 100 for stable percentiles, got {n_paths}")
    if any(c <= 0 for c in closes):
        raise ValueError("all closes must be > 0")

    window = closes[-(lookback + 1):]
    rets = [window[i] / window[i - 1] - 1.0 for i in range(1, len(window))]
    if len(rets) < min_history:
        raise ValueError(
            f"need at least {min_history} daily returns to resample, got {len(rets)} "
            "— widen the history"
        )
    if block_days > len(rets):
        raise ValueError(
            f"block_days={block_days} exceeds available returns ({len(rets)})"
        )

    rng = random.Random(seed)
    last_start = len(rets) - block_days
    terminals: list[float] = []
    for _ in range(n_paths):
        path: list[float] = []
        while len(path) < horizon_days:
            start = rng.randint(0, last_start)
            path.extend(rets[start:start + block_days])
        growth = 1.0
        for r in path[:horizon_days]:
            growth *= 1.0 + r
        terminals.append(growth - 1.0)

    qs = quantiles(terminals, n=100, method="inclusive")
    pct = {k: qs[i] for k, i in _PCT_INDEX.items()}
    last_close = closes[-1]
    return BootstrapBands(
        n_paths=n_paths,
        block_days=block_days,
        seed=seed,
        horizon_days=horizon_days,
        history_days=len(rets),
        percentiles=pct,
        band_prices={k: last_close * (1.0 + v) for k, v in pct.items()},
        up_frac=sum(1 for t in terminals if t > 0) / len(terminals),
        note=(
            f"{n_paths} block-bootstrap paths (blocks of {block_days} contiguous "
            f"days, seed {seed}) resampled from the trailing {len(rets)} daily "
            "returns — recombinations of the PAST, not a forecast; regimes history "
            "never contained cannot appear here."
        ),
    )


def expected_move(
    closes: Sequence[float],
    dates: Sequence[str],
    *,
    horizon_days: int = 5,
    lookback: int = 252,
    vol_window: int = 20,
    min_samples: int = 20,
) -> ExpectedMoveReading:
    """Distribution of trailing horizon-day returns as of the LAST bar."""
    n = len(closes)
    if len(dates) != n:
        raise ValueError("closes and dates must be equal length")
    if horizon_days < 1 or lookback < 2 or vol_window < 2 or min_samples < 2:
        raise ValueError(
            "horizon_days >= 1, lookback >= 2, vol_window >= 2, min_samples >= 2"
        )
    if any(c <= 0 for c in closes):
        raise ValueError("all closes must be > 0")

    first_start = max(0, n - horizon_days - lookback)
    starts = range(first_start, n - horizon_days)
    samples = [closes[i + horizon_days] / closes[i] - 1.0 for i in starts]
    if len(samples) < min_samples:
        raise ValueError(
            f"need at least {min_samples} overlapping {horizon_days}-day samples, "
            f"got {len(samples)} — widen the history"
        )
    last_close = closes[-1]
    unconditional = _bands(samples, last_close)

    # vol-tercile conditioning (volatility clusters)
    def vol_at(i: int) -> float | None:
        if i < vol_window:
            return None
        window = closes[i - vol_window: i + 1]
        rets = [window[j] / window[j - 1] - 1.0 for j in range(1, len(window))]
        return stdev(rets)

    tagged = [(vol_at(i), s) for i, s in zip(starts, samples)]
    tagged = [(v, s) for v, s in tagged if v is not None]
    current_vol = vol_at(n - 1)
    tercile = None
    conditioned = None
    if current_vol is not None and len(tagged) >= 3:
        vols = sorted(v for v, _ in tagged)
        cut1 = vols[len(vols) // 3]
        cut2 = vols[(2 * len(vols)) // 3]

        def bucket(v: float) -> str:
            return "low" if v <= cut1 else ("mid" if v <= cut2 else "high")

        tercile = bucket(current_vol)
        subset = [s for v, s in tagged if bucket(v) == tercile]
        if len(subset) >= min_samples:
            conditioned = _bands(subset, last_close)

    return ExpectedMoveReading(
        horizon_days=horizon_days,
        lookback_days=lookback,
        vol_window=vol_window,
        as_of_date=dates[-1],
        last_close=last_close,
        unconditional=unconditional,
        current_vol_tercile=tercile,
        conditioned=conditioned,
        note=(
            f"Historical distribution of overlapping {horizon_days}-day returns — "
            "NOT a forecast. Overlapping samples are autocorrelated and understate "
            "tail risk; the future can exceed every band shown."
        ),
    )
