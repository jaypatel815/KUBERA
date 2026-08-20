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
from datetime import date

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
    # T116b: scheduled events falling INSIDE the window, each a named
    # caveat — bands drawn from ordinary days do not price a binary print
    event_notes: list[str] = field(default_factory=list)


def _event_notes(as_of_date: str | None, upcoming, horizons,
                 measured: dict[str, str] | None) -> list[str]:
    """T116b — events (same dict[str, list[str]] calendar shape every
    consumer uses, with_fomc output included) that land within max(horizons)
    days of as-of. Each becomes a caveat; a measured-reaction sentence is
    attached when the caller has one, otherwise the absence is NAMED and
    routed to the surface that measures it."""
    if not as_of_date or not upcoming:
        return []
    try:
        asof = date.fromisoformat(str(as_of_date)[:10])
    except ValueError:
        return []
    hmax = max(horizons)
    notes: list[str] = []
    for name in sorted(upcoming):
        for d in upcoming[name]:
            try:
                ev = date.fromisoformat(str(d)[:10])
            except ValueError:
                continue
            days_until = (ev - asof).days
            if not 0 <= days_until <= hmax:
                continue
            when = "TODAY" if days_until == 0 else f"in {days_until}d"
            line = (f"{name} {when} ({ev.isoformat()}) is inside the "
                    f"{hmax}d window - these bands are drawn from ordinary "
                    "days and do not price the event")
            extra = (measured or {}).get(name)
            if extra:
                line += f"; measured reaction: {extra}"
            else:
                line += ("; no measured reaction attached - "
                         "get_earnings_preview has this symbol's own base "
                         "rates when they exist")
            notes.append(line)
    return notes


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
                       horizons=DEFAULT_HORIZONS,
                       upcoming: dict[str, list[str]] | None = None,
                       measured: dict[str, str] | None = None,
                       ) -> ShortHorizonRead:
    """The leading read. Refuses per-horizon by name; an empty-history
    symbol yields a read whose every horizon says why. `upcoming` is the
    standard event calendar (T116b): events inside the window become named
    caveats on the read — the bands stay untouched, honesty rides beside
    them."""
    symbol = symbol.upper()
    if not closes:
        return ShortHorizonRead(
            symbol=symbol, last_close=None, as_of_date=None,
            horizons=[HorizonRead(horizon_days=h, available=False,
                                  why="no price history")
                      for h in horizons])
    reads = [_one_horizon(closes, dates, h) for h in horizons]
    as_of = str(dates[-1])[:10] if dates else None
    return ShortHorizonRead(
        symbol=symbol,
        last_close=float(closes[-1]),
        as_of_date=as_of,
        horizons=reads,
        event_notes=_event_notes(as_of, upcoming, horizons, measured),
    )


def one_line(read: ShortHorizonRead) -> str:
    """A single terminal-friendly line for the monitor: the days lens,
    first. Uses the shortest AVAILABLE horizon; names the refusal if none."""
    suffix = f"  !! {read.event_notes[0]}" if read.event_notes else ""
    for h in read.horizons:
        if h.available and h.p05_frac is not None and h.p95_frac is not None:
            odds = f"{h.up_odds:.0%}" if h.up_odds is not None else "?"
            return (f"next {h.horizon_days}d usually {h.p05_frac:+.1%}"
                    f"..{h.p95_frac:+.1%} from here; up-odds {odds} "
                    f"({h.basis}, n={h.samples}) - odds, not a prediction"
                    f"{suffix}")
    why = read.horizons[0].why if read.horizons else "no horizons"
    return f"next-days read unavailable: {why}{suffix}"
