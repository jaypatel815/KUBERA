"""T076b — FOMC decision dates as a published-schedule table (D016/D019).

SOURCE DECISION (the one T076 deferred): FRED has no FOMC meeting-date API,
and scraping federalreserve.gov is fragile against redesigns. But the Fed
PUBLISHES its meeting calendar years ahead, and the dates are external-spec
constants exactly like the exchange holiday table in data/statements.py —
public facts that change ~once a year, transcribed with a source note and
guarded against silent staleness. Free, keyless, deterministic (D034).

TRANSCRIBED from the Federal Reserve's published "Meeting calendars"
(federalreserve.gov/monetarypolicy/fomccalendars.htm) on 2026-08-18.
Each entry is the DECISION day (day 2 of the meeting — the statement lands
14:00 ET; the tape cares about that day). REVIEWER CHECK: open the Fed page
and compare these 16 rows — a mistyped date here mis-guards real entries.
THE CHECK ALREADY EARNED ITS KEEP (I031): the first transcription had June
2027 as the 16th; the reviewer's live fetch of the Fed page (updated
2026-07-29) showed the meeting as June 8-9 — decision day 2027-06-09,
corrected 2026-08-19. All 16 rows now match that live fetch.

STALENESS IS SELF-REPORTED: fomc_staleness_note() warns when the table's
horizon is within STALE_WARN_DAYS of running out, so the "rule with no
mechanism" failure (D031) cannot recur here — every brief carries the nag
until someone appends the next published year.
"""

from __future__ import annotations

from datetime import date

FOMC_NAME = "FOMC decision"
STALE_WARN_DAYS = 90        # start nagging ~a quarter before the table ends

# Decision days (day 2). Append next year's rows when the Fed publishes them.
FOMC_DECISION_DATES: tuple[str, ...] = (
    # 2026
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
    # 2027
    "2027-01-27", "2027-03-17", "2027-04-28", "2027-06-09",
    "2027-07-28", "2027-09-15", "2027-10-27", "2027-12-08",
)


def with_fomc(dates_by_name: dict[str, list[str]] | None) -> dict[str, list[str]]:
    """Merge the FOMC table into a release calendar (never mutates the input).

    Every calendar consumer (event guard, briefs, macro tool) goes through
    dict[str, list[str]] — one merge helper keeps the table out of their code.
    """
    merged: dict[str, list[str]] = dict(dates_by_name or {})
    merged[FOMC_NAME] = list(FOMC_DECISION_DATES)
    return merged


def fomc_staleness_note(today: date) -> str | None:
    """None while the table comfortably covers the future; a nag otherwise."""
    last = date.fromisoformat(FOMC_DECISION_DATES[-1])
    days_left = (last - today).days
    if days_left < 0:
        return (f"FOMC table EXHAUSTED (last entry {last.isoformat()}) — the "
                "event guard is blind to FOMC until next year's published "
                "calendar is appended to analysis/fomc.py")
    if days_left <= STALE_WARN_DAYS:
        return (f"FOMC table ends {last.isoformat()} ({days_left} days) — "
                "append the Fed's next published calendar to analysis/fomc.py")
    return None


def priced_for_perfection(runup_frac: float | None,
                          p95_frac: float | None) -> dict | None:
    """D019's sell-the-news ingredient, from two numbers that already exist.

    A pre-event runup at or beyond the symbol's own p95 expected 5-day move
    means the tape has already paid for a good outcome — the asymmetric risk
    is a "sell the news" fade even on a beat. Returns a labelled dict, or
    None when either input is missing (never guessed). This FLAGS; it never
    predicts, and the note says so.
    """
    if runup_frac is None or p95_frac is None or p95_frac <= 0:
        return None
    hot = runup_frac >= p95_frac
    return {
        "flag": hot,
        "runup_5d_frac": round(runup_frac, 6),
        "p95_5d_frac": round(p95_frac, 6),
        "note": ("pre-event runup >= own p95 5-day move — priced for "
                 "perfection; good news may already be paid for (D019). "
                 "A flag, not a forecast."
                 if hot else
                 "runup within normal range vs own 5-day distribution"),
    }
