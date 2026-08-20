"""T116 — the short-horizon read: KUBERA's LEADING lens (D035, owner-set).

The owner trades days, not quarters. After his first live monitor run
(I033) he said it plainly: lead with what the next days usually look like.
This module packages T077's conditioned distributions into that leading
read: "from HERE, the next 1-3 days usually range X..Y; up-odds Z; typical
move |M|" — preferring the CURRENT-vol-tercile conditioned bands (T077's
edge: volatility clusters) and SAYING which bands answered.

DOCTRINE UNCHANGED (D017/D035): odds and ranges, never point predictions.
"SPY at 770 tomorrow" is the confidence trick; the distribution from here
is information the owner can size against. When asked "which way will it
go", the honest answer IS this read plus one sentence on why a point call
is refused. Thin history refuses by horizon, named, never padded.

Pure: caller supplies closes/dates; every surface (tool, monitor, brief,
briefing) composes from the same function so the numbers can never differ
between what chat says and what the monitor prints.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from analysis.expected_move import expected_move

DEFAULT_HORIZONS = (1, 3)


@dataclass(frozen=True)
class HorizonRead:
    horizon_days: int
    available: bool
    why: str | None                  # named refusal when unavailable
    samples: int | None = None
    basis: str | None = None         # "vol-conditioned (high tercile)" | "unconditional"
    p05_frac: float | None = None
    p95_frac: float | None = None
    p05_price: float | None = None
    p95_price: float | None = None
    typical_abs_move_frac: float | None = None
    up_odds: float | None = None
    payoff_ratio: float | None = None


@dataclass(frozen=True)
class ShortHorizonRead:
    symbol: str
    last_close: float | None
    as_of_date: str | None
    horizons: list[HorizonRead] = field(default_factory=list)
    note: str = ("the DAYS lens leads (D035, owner-set): odds and ranges "
                 "from this symbol's own history, never point predictions - "
                 "'which way' is answered with this distribution and the "
                 "honest sentence that point calls are refused (D017)")


def _one_horizon(closes, dates, h: int) -> HorizonRead:
    try:
        em = expected_move(closes, dates, horizon_days=h)
    except ValueError as e:
        return HorizonRead(horizon_days=h, available=False,
                           why=f"insufficient history ({e})")
    if em.conditioned is not None and em.current_vol_tercile is not None:
        bands = em.conditioned
        basis = f"vol-conditioned ({em.current_vol_tercile} tercile)"
    else:
        bands = em.unconditional
        basis = "unconditional (thin same-tercile history)"
    return HorizonRead(
        horizon_days=h, available=True, why=None,
        samples=bands.samples, basis=basis,
        p05_frac=bands.percentiles.get("p05"),
        p95_frac=bands.percentiles.get("p95"),
        p05_price=bands.band_prices.get("p05"),
        p95_price=bands.band_prices.get("p95"),
        typical_abs_move_frac=bands.expected_abs_move_frac,
        up_odds=bands.up_frac,
        payoff_ratio=bands.payoff_ratio,
    )


def short_horizon_read(symbol: str, closes, dates,
                       horizons=DEFAULT_HORIZONS) -> ShortHorizonRead:
    """The leading read. Refuses per-horizon by name; an empty-history
    symbol yields a read whose every horizon says why."""
    symbol = symbol.upper()
    if not closes:
        return ShortHorizonRead(
            symbol=symbol, last_close=None, as_of_date=None,
            horizons=[HorizonRead(horizon_days=h, available=False,
                                  why="no price history")
                      for h in horizons])
    reads = [_one_horizon(closes, dates, h) for h in horizons]
    return ShortHorizonRead(
        symbol=symbol,
        last_close=float(closes[-1]),
        as_of_date=str(dates[-1])[:10] if dates else None,
        horizons=reads,
    )


def one_line(read: ShortHorizonRead) -> str:
    """A single terminal-friendly line for the monitor: the days lens,
    first. Uses the shortest AVAILABLE horizon; names the refusal if none."""
    for h in read.horizons:
        if h.available and h.p05_frac is not None and h.p95_frac is not None:
            odds = f"{h.up_odds:.0%}" if h.up_odds is not None else "?"
            return (f"next {h.horizon_days}d usually {h.p05_frac:+.1%}"
                    f"..{h.p95_frac:+.1%} from here; up-odds {odds} "
                    f"({h.basis}, n={h.samples}) - odds, not a prediction")
    why = read.horizons[0].why if read.horizons else "no horizons"
    return f"next-days read unavailable: {why}"
