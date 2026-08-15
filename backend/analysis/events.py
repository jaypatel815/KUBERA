"""Event-risk guard (T076, D016/D019) — don't open new risk into a known storm.

Scheduled macro releases (CPI, the Employment Situation report) move the whole
tape; the doctrine's answer is not prediction but POSITIONING: pause new
entries in a configurable window before and on the release day. Sells are
never blocked — reducing risk is always allowed.

Pure date arithmetic over release calendars fetched elsewhere (data/fred.py).
Calendar days, deliberately: a Monday release guards from the weekend, which
errs conservative. FOMC meeting dates are NOT here — FRED has no meeting-date
API; that source decision is T076b.
"""

from dataclasses import dataclass
from datetime import date

DEFAULT_WINDOW_BEFORE = 1   # pause new entries this many calendar days before
DEFAULT_HORIZON_DAYS = 14   # how far ahead briefings look


@dataclass(frozen=True)
class EventRisk:
    name: str
    date: str        # YYYY-MM-DD
    days_away: int   # 0 = release day


def upcoming_events(dates_by_name: dict[str, list[str]], today: date,
                    horizon_days: int = DEFAULT_HORIZON_DAYS) -> list[EventRisk]:
    """All known releases from today through the horizon, soonest first."""
    if horizon_days < 0:
        raise ValueError("horizon_days must be >= 0")
    out = []
    for name, dates in dates_by_name.items():
        for d in set(dates):
            days = (date.fromisoformat(d) - today).days
            if 0 <= days <= horizon_days:
                out.append(EventRisk(name=name, date=d, days_away=days))
    return sorted(out, key=lambda e: (e.days_away, e.name))


def entry_guard(dates_by_name: dict[str, list[str]], today: date,
                window_before: int = DEFAULT_WINDOW_BEFORE) -> list[str]:
    """Reasons to pause NEW entries: any release today or within the window.
    Empty list = clear to trade."""
    if window_before < 0:
        raise ValueError("window_before must be >= 0")
    reasons = []
    for ev in upcoming_events(dates_by_name, today, horizon_days=window_before):
        when = ("today" if ev.days_away == 0
                else "tomorrow" if ev.days_away == 1
                else f"in {ev.days_away} days")
        reasons.append(f"event window: {ev.name} release {ev.date} ({when})")
    return reasons
