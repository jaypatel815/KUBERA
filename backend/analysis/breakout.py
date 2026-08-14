"""Breakout detector (T053) — the doctrine's three-part test, as events.

A real breakout needs (docs/research/regime-trading-notes.md): (1) price escapes
the established range, (2) volume suddenly expands, (3) price HOLDS outside the
prior range. T050 checks (1)+(2) for the current bar; this module scans history
and emits breakout EVENTS with all three judged — so chat can say "SPY broke above
505 three sessions ago on 2.1x volume and has held since", and T054's router can
consume them.

Definitions (stable contracts):
- An event starts at bar i when close[i] is strictly outside the extremes of the
  PRIOR `range_lookback` bars while close[i-1] was NOT outside its own prior
  window — fresh escapes only; continuation bars extend the event, never start one.
- rvol_at_break = volume[i] / mean(volume of the prior `rvol_baseline` bars);
  None when the baseline is zero. Thresholds shared with the regime classifier
  (RVOL_CONFIRM, RVOL_FAKEOUT) — one source of truth.
- held_bars = consecutive post-break closes strictly beyond the boundary.
- status, judged on the first `hold_confirm` bars after the break:
    "confirmed"   held >= hold_confirm AND volume-confirmed — the full pattern
    "failed"      a close returned to/through the boundary within the window —
                  the fakeout completed (the $100 -> $106 -> $99 lesson)
    "unconfirmed" held, but volume never confirmed — doctrine says stay suspicious
    "pending"     fewer than hold_confirm bars exist after the break
  Status is judged once on the window and not rewritten by later price action;
  held_bars keeps counting so narration can report how long it lasted.

Pure deterministic code; bad input raises ValueError (fail closed).
"""

from dataclasses import dataclass
from statistics import mean
from typing import Sequence

from analysis.regime import RVOL_CONFIRM, RVOL_FAKEOUT


@dataclass(frozen=True)
class BreakoutEvent:
    date: str
    direction: str            # "up" | "down"
    boundary: float           # the prior-range extreme that was broken
    close_at_break: float
    rvol_at_break: float | None
    volume_confirmed: bool    # rvol_at_break >= RVOL_CONFIRM
    suspected_fakeout: bool   # rvol_at_break < RVOL_FAKEOUT at the break
    held_bars: int            # consecutive post-break closes beyond the boundary
    status: str               # "confirmed" | "failed" | "unconfirmed" | "pending"
    reason: str


@dataclass(frozen=True)
class BreakoutScan:
    as_of_date: str
    bars_used: int
    range_lookback: int
    rvol_baseline: int
    hold_confirm: int
    events: list[BreakoutEvent]   # chronological
    latest: BreakoutEvent | None
    active: bool  # latest event not failed AND last close still beyond its boundary


def _escaped(closes, highs, lows, i: int, lookback: int) -> str | None:
    if i < lookback:
        return None
    prior_high = max(highs[i - lookback: i])
    prior_low = min(lows[i - lookback: i])
    if closes[i] > prior_high:
        return "up"
    if closes[i] < prior_low:
        return "down"
    return None


def detect_breakouts(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
    dates: Sequence[str],
    *,
    range_lookback: int = 20,
    rvol_baseline: int = 20,
    hold_confirm: int = 2,
) -> BreakoutScan:
    """Scan the series for breakout events (oldest first). Pass enough history to
    cover the range window plus whatever depth of events you care about."""
    n = len(closes)
    if not (len(highs) == len(lows) == n == len(volumes) == len(dates)):
        raise ValueError("highs, lows, closes, volumes, dates must be equal length")
    if range_lookback < 2 or rvol_baseline < 1 or hold_confirm < 1:
        raise ValueError("range_lookback >= 2, rvol_baseline >= 1, hold_confirm >= 1")
    min_bars = max(range_lookback, rvol_baseline) + 1
    if n < min_bars:
        raise ValueError(f"need at least {min_bars} bars for these lookbacks, got {n}")
    for i in range(n):
        if highs[i] <= 0 or lows[i] <= 0 or closes[i] <= 0:
            raise ValueError(f"bar {i} ({dates[i]}): prices must be > 0")
        if lows[i] > highs[i]:
            raise ValueError(f"bar {i} ({dates[i]}): low {lows[i]} > high {highs[i]}")
        if volumes[i] < 0:
            raise ValueError(f"bar {i} ({dates[i]}): volume must be >= 0")

    events: list[BreakoutEvent] = []
    start = max(range_lookback, rvol_baseline)
    for i in range(start, n):
        direction = _escaped(closes, highs, lows, i, range_lookback)
        if direction is None:
            continue
        if _escaped(closes, highs, lows, i - 1, range_lookback) == direction:
            continue  # continuation of an existing move, not a fresh escape

        if direction == "up":
            boundary = max(highs[i - range_lookback: i])
        else:
            boundary = min(lows[i - range_lookback: i])

        base = volumes[i - rvol_baseline: i]
        base_mean = mean(base)
        rvol = (volumes[i] / base_mean) if base_mean > 0 else None
        volume_confirmed = rvol is not None and rvol >= RVOL_CONFIRM
        suspected = rvol is not None and rvol < RVOL_FAKEOUT

        # hold-outside tracking after the break
        def outside(c: float) -> bool:
            return c > boundary if direction == "up" else c < boundary

        held = 0
        for j in range(i + 1, n):
            if outside(closes[j]):
                held += 1
            else:
                break

        post = n - 1 - i  # bars available after the break
        window = min(post, hold_confirm)
        returned_in_window = any(
            not outside(closes[j]) for j in range(i + 1, i + 1 + window)
        )
        if returned_in_window:
            status = "failed"
        elif post < hold_confirm:
            status = "pending"
        elif volume_confirmed:
            status = "confirmed"
        else:
            status = "unconfirmed"

        word = "above" if direction == "up" else "below"
        rvol_txt = f"{rvol:.2f}x volume" if rvol is not None else "unknown volume"
        status_txt = {
            "confirmed": f"held {held} bar(s) with volume confirmation",
            "failed": "price returned inside the range — the fakeout completed",
            "unconfirmed": f"held {held} bar(s) but volume never confirmed — stay suspicious",
            "pending": "too recent to judge the hold",
        }[status]
        events.append(BreakoutEvent(
            date=dates[i],
            direction=direction,
            boundary=boundary,
            close_at_break=closes[i],
            rvol_at_break=rvol,
            volume_confirmed=volume_confirmed,
            suspected_fakeout=suspected,
            held_bars=held,
            status=status,
            reason=(
                f"close {closes[i]} escaped {word} the prior {range_lookback}-bar "
                f"boundary {boundary} on {rvol_txt}; {status_txt}"
            ),
        ))

    latest = events[-1] if events else None
    active = False
    if latest is not None and latest.status != "failed":
        last = closes[-1]
        active = last > latest.boundary if latest.direction == "up" else last < latest.boundary
    return BreakoutScan(
        as_of_date=dates[-1],
        bars_used=n,
        range_lookback=range_lookback,
        rvol_baseline=rvol_baseline,
        hold_confirm=hold_confirm,
        events=events,
        latest=latest,
        active=active,
    )
