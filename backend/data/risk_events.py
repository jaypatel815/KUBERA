"""T135 — the risk-event log: history for the D021 revisit, written as it
happens. Observation-based by design: the risk ENGINE stays a pure state
machine (its tests never touch a DB), and the brief's risk section — which
already restores the engine and computes the tier every run — observes and
appends. Named limitation: an event's `ts` is the OBSERVATION time; for
breaker trips the trip's own clock is inside the recorded reason text.

Dedupe rules keep repeated observations honest:
- tier_change appends only when the observed level differs from the LAST
  recorded level (first observation records the starting tier).
- breaker_trip appends only when the trip reason differs from the last
  recorded one (a trip observed by five brief runs is ONE event).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from data.models import RiskEvent

TIER_CHANGE = "tier_change"
BREAKER_TRIP = "breaker_trip"


def _last(session: Session, kind: str) -> RiskEvent | None:
    return session.execute(
        select(RiskEvent).where(RiskEvent.kind == kind)
        .order_by(RiskEvent.id.desc())
    ).scalars().first()


def append_event(session: Session, kind: str, detail: str,
                 ts: datetime | None = None) -> RiskEvent:
    row = RiskEvent(kind=kind, detail=detail[:400],
                    ts=ts or datetime.now(timezone.utc))
    session.add(row)
    session.commit()
    return row


def observe_tier(session: Session, level: int, name: str) -> RiskEvent | None:
    """Record a tier observation IF the level changed since last recorded.
    The detail encodes the level machine-readably: 'level=N name=...'."""
    last = _last(session, TIER_CHANGE)
    last_level = None
    if last is not None and "level=" in last.detail:
        try:
            last_level = int(last.detail.split("level=")[1].split()[0])
        except ValueError:
            last_level = None
    if last_level == level:
        return None
    return append_event(session, TIER_CHANGE, f"level={level} name={name}")


def observe_breaker(session: Session, tripped: bool,
                    reason: str | None) -> RiskEvent | None:
    """Record a breaker trip IF this trip isn't already on the record
    (same reason text = same trip, seen again)."""
    if not tripped or not reason:
        return None
    last = _last(session, BREAKER_TRIP)
    if last is not None and last.detail == reason[:400]:
        return None
    return append_event(session, BREAKER_TRIP, reason)


def events_between(session: Session, start: datetime,
                   end: datetime) -> list[RiskEvent]:
    return list(session.execute(
        select(RiskEvent).where(RiskEvent.ts >= start, RiskEvent.ts <= end)
        .order_by(RiskEvent.ts)
    ).scalars().all())
