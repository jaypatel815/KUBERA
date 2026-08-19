"""T083 — event reaction base rates. Every move hand-computed on tiny tapes."""

from dataclasses import dataclass
from datetime import date, timedelta

import pytest

from analysis.event_rates import MIN_EVENTS, RUNUP_BARS, compute_event_base_rates


@dataclass(frozen=True)
class Ev:
    date: date
    time_hint: str | None = None
    eps_actual: float | None = None
    eps_estimated: float | None = None


def weekdays(start: date, n: int) -> list[date]:
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


# 20 weekday bars, closes 100..119 (each bar +1 absolute).
DATES = weekdays(date(2026, 3, 2), 20)
CLOSES = [100.0 + i for i in range(20)]


def test_bmo_event_moves_its_own_bar_hand_computed():
    """Event on DATES[10] (bmo): move = closes[10]/closes[9]-1 = 110/109-1;
    next day = 111/110-1; runup = closes[9]/closes[4]-1 = 109/104-1."""
    ev = Ev(DATES[10], "bmo", eps_actual=2.0, eps_estimated=1.5)
    r = compute_event_base_rates("AAPL", [ev] * 4, DATES, CLOSES)  # 4 copies clear MIN
    assert r.verdict == "rates"
    rx = r.reactions[0]
    assert rx.reaction_date == DATES[10].isoformat()
    assert rx.event_day_move == pytest.approx(110 / 109 - 1, abs=1e-6)
    assert rx.next_day_move == pytest.approx(111 / 110 - 1, abs=1e-6)
    assert rx.pre_event_runup == pytest.approx(109 / 104 - 1, abs=1e-6)
    assert rx.outcome == "beat" and rx.timing_assumed is False


def test_amc_event_shifts_to_the_next_bar():
    """amc on DATES[10]: the reaction bar is DATES[11] — move 111/110-1."""
    ev = Ev(DATES[10], "amc", eps_actual=1.0, eps_estimated=1.5)
    r = compute_event_base_rates("X", [ev] * 4, DATES, CLOSES)
    rx = r.reactions[0]
    assert rx.reaction_date == DATES[11].isoformat()
    assert rx.event_day_move == pytest.approx(111 / 110 - 1, abs=1e-6)
    assert rx.outcome == "miss"


def test_weekend_event_rolls_to_monday_and_missing_hint_is_counted():
    """A Saturday event date (no bar) reacts on Monday; no time hint ->
    bmo assumed AND counted in timing_assumed."""
    saturday = DATES[4] + timedelta(days=(5 - DATES[4].weekday()))
    assert saturday.weekday() == 5
    ev = Ev(saturday, None)                    # no hint, no eps -> unknown
    r = compute_event_base_rates("X", [ev] * 4, DATES, CLOSES)
    rx = r.reactions[0]
    assert date.fromisoformat(rx.reaction_date).weekday() == 0   # Monday
    assert rx.timing_assumed is True
    assert r.timing_assumed_count == 4
    assert rx.outcome == "unknown"


def test_splits_and_closed_down_count_hand_computed():
    """Two beats on a falling tape + one miss on a rising one: the beat split
    must show 2 closed-down (the '6 of 8 beats still closed down' shape)."""
    dates = weekdays(date(2026, 3, 2), 12)
    closes = [100, 101, 99, 98, 100, 101, 99, 97, 98, 99, 100, 101]
    evs = [
        Ev(dates[2], "bmo", 2.0, 1.0),    # 99/101-1 < 0: beat, closed down
        Ev(dates[6], "bmo", 2.0, 1.0),    # 99/101-1 < 0: beat, closed down
        Ev(dates[10], "bmo", 1.0, 2.0),   # 100/99-1 > 0: miss, closed up
        Ev(dates[4], "bmo", 1.0, 1.0),    # inline
    ]
    r = compute_event_base_rates("X", evs, dates, [float(c) for c in closes])
    assert r.verdict == "rates"
    beat = r.by_outcome["beat"]
    assert beat.n == 2 and beat.closed_down_count == 2
    assert r.by_outcome["miss"].n == 1
    assert r.by_outcome["miss"].closed_down_count == 0
    assert r.by_outcome["inline"].n == 1
    assert r.by_outcome["unknown"].n == 0


def test_refuses_under_min_events_with_the_anecdote_note():
    ev = Ev(DATES[10], "bmo", 2.0, 1.5)
    r = compute_event_base_rates("X", [ev] * (MIN_EVENTS - 1), DATES, CLOSES)
    assert r.verdict == "insufficient_history"
    assert r.by_outcome == {}
    assert "anecdote" in r.note


def test_unmeasurable_events_reported_never_dropped():
    """An event after the last bar and one before the first are both
    unmeasured with a why; measurable ones still compute."""
    evs = ([Ev(DATES[-1] + timedelta(days=30), "bmo", 1.0, 1.0)]
           + [Ev(DATES[0] - timedelta(days=9), "bmo", 1.0, 1.0)]
           + [Ev(DATES[10], "bmo", 2.0, 1.0)] * 4)
    r = compute_event_base_rates("X", evs, DATES, CLOSES)
    assert len(r.unmeasured) == 2
    whys = " | ".join(u["why"] for u in r.unmeasured)
    assert "no bar at or after" in whys and "FIRST bar" in whys
    assert r.events_measured == 4


def test_edge_event_on_last_bar_has_no_next_day():
    ev = Ev(DATES[-1], "bmo", 2.0, 1.0)
    r = compute_event_base_rates("X", [ev] * 4, DATES, CLOSES)
    assert r.reactions[0].next_day_move is None


def test_short_history_runup_is_none_not_invented():
    dates = weekdays(date(2026, 3, 2), RUNUP_BARS)   # too short for a runup
    closes = [100.0 + i for i in range(RUNUP_BARS)]
    ev = Ev(dates[-1], "bmo", 2.0, 1.0)
    r = compute_event_base_rates("X", [ev] * 4, dates, closes)
    assert r.reactions[0].pre_event_runup is None


def test_input_validation():
    with pytest.raises(ValueError, match="align"):
        compute_event_base_rates("X", [], DATES, CLOSES[:-1])
    with pytest.raises(ValueError, match="ascending"):
        compute_event_base_rates("X", [], list(reversed(DATES)), CLOSES)
