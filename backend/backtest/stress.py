"""T064b-rest — crisis-window stress runs (the last open T064b item).

A promotion earned on calm history says nothing about 2020-March behavior.
This module re-runs a template over NAMED crisis windows and puts the
numbers beside a buy-and-hold of the SAME window — the honest question is
"did the strategy protect anything, or just track the crash with extra
steps?" Every run also shows itself at 2x costs (T109b house rule).

MEASUREMENT ONLY: stress results are evidence for the owner, recorded
nowhere — they neither promote nor demote (live demotion is T093's CUSUM,
judged on live results, not history replays).

FEED HONESTY (the ticket's own words): 2008 is IMPOSSIBLE on this feed —
Alpaca's IEX history does not reach it. It is listed as impossible BY NAME
rather than silently substituted with a different crisis. And a window is
only measured when the feed actually COVERS it: if history starts after
the window opens, the run refuses with the feed's first date, because a
partial crash is a different (easier) test.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Sequence

from backtest.engine import run_backtest
from backtest.strategies import build_strategy

# Windows chosen for regime coverage: the fastest crash on record, and a
# year-long grind. Dates are the first/last trading days of the episodes.
WINDOWS: tuple["StressWindow", ...] = ()   # populated below (dataclass first)

IMPOSSIBLE_WINDOWS: tuple[tuple[str, str], ...] = (
    ("gfc-2008", "2008 predates this feed's history (IEX via Alpaca) — "
                 "unmeasurable HERE; saying so beats substituting a "
                 "different crisis and calling it 2008"),
)

# Coverage tolerance: the feed's first bar may sit a few sessions after the
# nominal window start (holidays, listing gaps). Beyond this, refuse.
COVERAGE_TOLERANCE_DAYS = 7
MIN_WINDOW_BARS = 30


@dataclass(frozen=True)
class StressWindow:
    name: str
    start: str            # ISO date, inclusive
    end: str              # ISO date, inclusive
    why: str


WINDOWS = (
    StressWindow("covid-2020", "2020-01-02", "2020-06-30",
                 "the fastest ~34% drawdown on record plus the first "
                 "rebound — punishes slow exits and rewards nothing"),
    StressWindow("bear-2022", "2022-01-03", "2022-12-30",
                 "a year-long grind of lower highs — punishes buy-the-dip "
                 "and premature re-entries"),
)


class CoverageError(ValueError):
    """The feed does not cover the requested window — named, never padded."""


def slice_window(dates: Sequence[str], closes: Sequence[float],
                 window: StressWindow) -> tuple[list[str], list[float]]:
    """Inclusive date-slice with coverage enforcement. `dates` ISO,
    ascending (the market-data contract). Refuses when the feed starts too
    late, ends too early, or leaves too few bars — a partial crash is a
    different, easier test."""
    if len(dates) != len(closes):
        raise ValueError("dates and closes must be equal length")
    pairs = [(d, c) for d, c in zip(dates, closes)
             if window.start <= d <= window.end]
    if not pairs:
        raise CoverageError(
            f"{window.name}: feed returned no bars inside "
            f"{window.start}..{window.end}"
            + (f" (feed starts {dates[0]})" if dates else " (feed empty)"))
    first, last = pairs[0][0], pairs[-1][0]
    tol = timedelta(days=COVERAGE_TOLERANCE_DAYS)
    if date.fromisoformat(first) > date.fromisoformat(window.start) + tol:
        raise CoverageError(
            f"{window.name}: feed's first bar in-window is {first}, more "
            f"than {COVERAGE_TOLERANCE_DAYS} days after the window opens "
            f"({window.start}) — refusing a partial crash")
    if date.fromisoformat(last) < date.fromisoformat(window.end) - tol:
        raise CoverageError(
            f"{window.name}: feed's last bar in-window is {last}, more than "
            f"{COVERAGE_TOLERANCE_DAYS} days before the window closes "
            f"({window.end}) — refusing a truncated episode")
    if len(pairs) < MIN_WINDOW_BARS:
        raise CoverageError(
            f"{window.name}: only {len(pairs)} bars in window "
            f"(need {MIN_WINDOW_BARS})")
    return [d for d, _ in pairs], [c for _, c in pairs]


@dataclass(frozen=True)
class StressRun:
    cumulative_return: float
    max_drawdown_frac: float
    sharpe_ann: float | None
    n_rebalances: int


@dataclass(frozen=True)
class StressReport:
    window: str
    template: str
    symbol: str
    bars: int
    first_date: str
    last_date: str
    strategy: StressRun
    strategy_2x_cost: StressRun          # T109b: every run shows 2x costs
    buy_and_hold: StressRun              # same window, the honest comparator
    drawdown_saved_frac: float           # b&h dd - strategy dd (>0 = protected)
    note: str = ("measurement only — recorded nowhere; neither promotes nor "
                 "demotes (live demotion is T093 CUSUM)")


def _run(closes, dates, strategy, name, cost_bps) -> StressRun:
    r = run_backtest(closes, dates, strategy, strategy_name=name,
                     cost_bps=cost_bps)
    return StressRun(cumulative_return=r.cumulative_return,
                     max_drawdown_frac=r.max_drawdown_frac,
                     sharpe_ann=r.sharpe_ann,
                     n_rebalances=r.n_rebalances)


def stress_template(template: str, symbol: str, dates: Sequence[str],
                    closes: Sequence[float], window: StressWindow,
                    cost_bps: float = 5.0) -> StressReport:
    """One (template, symbol, window) stress report. Raises CoverageError
    when the feed cannot honestly answer, ValueError on unknown templates."""
    wdates, wcloses = slice_window(dates, closes, window)
    strat = _run(wcloses, wdates, build_strategy(template), template, cost_bps)
    stressed = _run(wcloses, wdates, build_strategy(template),
                    f"{template}@2x", cost_bps * 2)
    bench = _run(wcloses, wdates, build_strategy("buy_and_hold"),
                 "buy_and_hold", cost_bps)
    return StressReport(
        window=window.name, template=template, symbol=symbol.upper(),
        bars=len(wcloses), first_date=wdates[0], last_date=wdates[-1],
        strategy=strat, strategy_2x_cost=stressed, buy_and_hold=bench,
        drawdown_saved_frac=bench.max_drawdown_frac - strat.max_drawdown_frac,
    )
