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


# ---------------------------------------------------------------- T121

PERIOD_MATCH_MAX_DAYS = 120   # a report lands 2-8 weeks after period end;
                              # 120d is a generous ceiling, NOT a guess knob


def enrich_from_surprises(session: Session, symbol: str, surprises) -> dict:
    """T121 — fold Finnhub actual-vs-estimate history into the store under
    an UNAMBIGUOUS-MATCH rule (T102: fail closed, never guess):

    Finnhub rows carry the fiscal PERIOD END; the store keys on REPORT
    dates. A surprise enriches THE stored event whose event_date falls in
    (period_end, period_end + 120d] ONLY when exactly one such event
    exists. Zero candidates -> counted unmatched; two or more -> counted
    ambiguous and SKIPPED (guessing which report a quarter belongs to is
    how beat/miss splits get silently wrong). Enrich-only-empty: existing
    non-null eps values are never overwritten (counted as already)."""
    from datetime import date as _date
    from datetime import timedelta as _td

    rows = stored_events(session, symbol)
    dated = []
    for r in rows:
        try:
            dated.append((_date.fromisoformat(r.event_date), r))
        except ValueError:
            continue

    out = {"enriched": 0, "ambiguous": 0, "unmatched": 0, "already": 0}
    for s in surprises:
        lo, hi = s.period_end, s.period_end + _td(days=PERIOD_MATCH_MAX_DAYS)
        cands = [r for d, r in dated if lo < d <= hi]
        if not cands:
            out["unmatched"] += 1
            continue
        if len(cands) > 1:
            out["ambiguous"] += 1
            continue
        row = cands[0]
        changed = False
        if row.eps_actual is None and s.eps_actual is not None:
            row.eps_actual = s.eps_actual
            changed = True
        if row.eps_estimated is None and s.eps_estimated is not None:
            row.eps_estimated = s.eps_estimated
            changed = True
        out["enriched" if changed else "already"] += 1
    session.commit()
    return out
