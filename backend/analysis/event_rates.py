"""T083 — event reaction base rates (D019): "should I hold through earnings",
answered from HIS OWN bars, as base rates. No prediction is claimed anywhere —
"6 of the last 8 beats still closed down" is evidence about the past, and the
note in every payload says exactly that.

Conventions, chosen and written down:
- REACTION DAY: an "amc" (after-close) report moves the NEXT trading bar; a
  "bmo" (before-open) report moves the bar of its own date. Missing/other
  time hints are treated as bmo AND COUNTED in `timing_assumed` — the shift
  matters (an amc reaction booked on the wrong day would smear every number),
  so the assumption is visible, never silent.
- EVENT-DAY MOVE: close[reaction_day] / close[reaction_day - 1] - 1.
- NEXT-DAY FOLLOW-THROUGH: close[reaction_day + 1] / close[reaction_day] - 1.
- PRE-EVENT RUNUP: the RUNUP_BARS-bar return INTO the last close before the
  reaction day — the "priced for perfection" ingredient (D019).
- BEAT/MISS: eps_actual vs eps_estimated when BOTH exist; otherwise the event
  lands in the "unknown" split. Never inferred from the price move — that
  would be circular.
- REFUSALS: fewer than MIN_EVENTS measurable events -> insufficient_history
  verdict with zero rates (the T069 precedent). An event whose reaction day
  is missing from the bars is REPORTED in `unmeasured`, never dropped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from statistics import median
from typing import Sequence

MIN_EVENTS = 4        # below this, base rates are anecdotes — refuse
RUNUP_BARS = 5        # ~one trading week into the event


@dataclass(frozen=True)
class EventReaction:
    event_date: str               # the REPORT date (calendar row)
    reaction_date: str            # the bar that absorbed it (amc -> next bar)
    outcome: str                  # "beat" | "miss" | "inline" | "unknown"
    event_day_move: float         # close-over-close on the reaction day
    next_day_move: float | None   # None when the event is the last bar
    pre_event_runup: float | None  # None when history is too short
    timing_assumed: bool          # True when the bmo default was applied


@dataclass(frozen=True)
class SplitRates:
    n: int
    median_event_move: float | None
    closed_down_count: int        # reaction day closed DOWN despite the split
    median_next_day: float | None


@dataclass(frozen=True)
class EventBaseRates:
    symbol: str
    verdict: str                  # "rates" | "insufficient_history"
    events_measured: int
    reactions: list[EventReaction] = field(default_factory=list)
    by_outcome: dict[str, SplitRates] = field(default_factory=dict)
    unmeasured: list[dict] = field(default_factory=list)
    timing_assumed_count: int = 0
    note: str = ("BASE RATES from this symbol's own history — a description "
                 "of the past, not a prediction. Sample sizes attached; "
                 "conventions: amc reports move the NEXT bar; beat/miss only "
                 "when both actual and estimated EPS exist.")


def _split(reactions: list[EventReaction], outcome: str) -> SplitRates:
    rs = [r for r in reactions if r.outcome == outcome]
    if not rs:
        return SplitRates(n=0, median_event_move=None, closed_down_count=0,
                          median_next_day=None)
    nexts = [r.next_day_move for r in rs if r.next_day_move is not None]
    return SplitRates(
        n=len(rs),
        median_event_move=round(median(r.event_day_move for r in rs), 6),
        closed_down_count=sum(1 for r in rs if r.event_day_move < 0),
        median_next_day=round(median(nexts), 6) if nexts else None,
    )


def compute_event_base_rates(
    symbol: str,
    events: Sequence,          # objects with .date, .time_hint, .eps_actual, .eps_estimated
    bar_dates: Sequence[date],
    closes: Sequence[float],
) -> EventBaseRates:
    """Pure: past earnings events + daily bars -> base rates.

    `bar_dates` must be ascending and aligned with `closes`. Events outside
    the bar history land in `unmeasured` with a why.
    """
    if len(bar_dates) != len(closes):
        raise ValueError("bar_dates and closes must align")
    if any(nxt <= prev for prev, nxt in zip(bar_dates, bar_dates[1:])):
        raise ValueError("bar_dates must be strictly ascending")

    index = {d: i for i, d in enumerate(bar_dates)}
    reactions: list[EventReaction] = []
    unmeasured: list[dict] = []
    assumed = 0

    for ev in events:
        ev_date: date = ev.date
        hint = (ev.time_hint or "").lower()
        timing_assumed = hint not in ("amc", "bmo")
        if timing_assumed:
            assumed += 1

        # Reaction bar: bmo/default -> the event date's own bar (or the next
        # bar at-or-after it, holidays included); amc -> strictly AFTER.
        if hint == "amc":
            later = [i for d, i in index.items() if d > ev_date]
        else:
            later = [i for d, i in index.items() if d >= ev_date]
        if not later:
            unmeasured.append({"event_date": ev_date.isoformat(),
                               "why": "no bar at or after the event date"})
            continue
        r = min(later)
        if r == 0:
            unmeasured.append({"event_date": ev_date.isoformat(),
                               "why": "reaction bar is the FIRST bar — no "
                                      "prior close to measure a move from"})
            continue

        event_move = closes[r] / closes[r - 1] - 1.0
        next_move = (closes[r + 1] / closes[r] - 1.0
                     if r + 1 < len(closes) else None)
        runup = (closes[r - 1] / closes[r - 1 - RUNUP_BARS] - 1.0
                 if r - 1 - RUNUP_BARS >= 0 else None)

        actual = getattr(ev, "eps_actual", None)
        est = getattr(ev, "eps_estimated", None)
        if actual is None or est is None:
            outcome = "unknown"
        elif actual > est:
            outcome = "beat"
        elif actual < est:
            outcome = "miss"
        else:
            outcome = "inline"

        reactions.append(EventReaction(
            event_date=ev_date.isoformat(),
            reaction_date=bar_dates[r].isoformat(),
            outcome=outcome,
            event_day_move=round(event_move, 6),
            next_day_move=round(next_move, 6) if next_move is not None else None,
            pre_event_runup=round(runup, 6) if runup is not None else None,
            timing_assumed=timing_assumed,
        ))

    if len(reactions) < MIN_EVENTS:
        return EventBaseRates(
            symbol=symbol.upper(), verdict="insufficient_history",
            events_measured=len(reactions), reactions=reactions,
            unmeasured=unmeasured, timing_assumed_count=assumed,
            note=(f"only {len(reactions)} measurable earnings reaction(s) — "
                  f"base rates need at least {MIN_EVENTS}; anything less is "
                  "an anecdote, and anecdotes are how superstitions start"),
        )

    reactions.sort(key=lambda r: r.event_date)
    return EventBaseRates(
        symbol=symbol.upper(), verdict="rates",
        events_measured=len(reactions), reactions=reactions,
        by_outcome={k: _split(reactions, k)
                    for k in ("beat", "miss", "inline", "unknown")},
        unmeasured=unmeasured, timing_assumed_count=assumed,
    )
