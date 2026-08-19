"""T083 — self-accumulated earnings history (the paywall answer).

The owner's probe measured it: FMP's FORWARD calendar answers on his tier,
PAST windows are paywalled. So every calendar fetch that flows through
KUBERA records what it saw, and the past assembles itself as quarters pass.
Dedupe per (symbol, event_date); a later fetch that carries eps_actual (or a
firmer time hint) BACKFILLS the stored row — the reported figure often
appears in the still-visible window shortly after the report.

record_calendar is BEST-EFFORT BY CONTRACT: it must never break the brief or
a tool call that only wanted the calendar. Failures return 0 and the caller
carries on; the store is an accumulator, not a dependency.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from data.models import EarningsObserved


def record_events(session: Session, events, source: str = "fmp-free") -> int:
    """Upsert calendar events; returns rows inserted or enriched."""
    changed = 0
    for ev in events:
        key_date = ev.date.isoformat()
        row = session.execute(
            select(EarningsObserved).where(
                EarningsObserved.symbol == ev.symbol,
                EarningsObserved.event_date == key_date)
        ).scalars().first()
        if row is None:
            session.add(EarningsObserved(
                symbol=ev.symbol, event_date=key_date,
                time_hint=ev.time_hint, eps_estimated=ev.eps_estimated,
                eps_actual=ev.eps_actual, source=source))
            changed += 1
            continue
        enriched = False
        if row.eps_actual is None and ev.eps_actual is not None:
            row.eps_actual = ev.eps_actual
            enriched = True
        if row.eps_estimated is None and ev.eps_estimated is not None:
            row.eps_estimated = ev.eps_estimated
            enriched = True
        if row.time_hint is None and ev.time_hint is not None:
            row.time_hint = ev.time_hint
            enriched = True
        if enriched:
            changed += 1
    session.commit()
    return changed


def record_calendar(session: Session | None, calendar) -> int:
    """Best-effort: record every event a fetched calendar carries."""
    if session is None:
        return 0
    try:
        return record_events(session, calendar.events)
    except Exception:
        # The store must never break the caller — it is an accumulator.
        return 0


def stored_events(session: Session, symbol: str) -> list[EarningsObserved]:
    """All observed dates for one symbol, oldest first."""
    return list(session.execute(
        select(EarningsObserved)
        .where(EarningsObserved.symbol == symbol.upper())
        .order_by(EarningsObserved.event_date)
    ).scalars().all())
