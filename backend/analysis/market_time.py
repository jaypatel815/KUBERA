"""T111 — market-day boundaries in market time (owner-reported).

The bug this ends: KUBERA stores every timestamp in UTC (correct, unchanged),
but several "today" boundaries were computed from the UTC DATE. At 11 PM
Eastern it is already 3 AM tomorrow in UTC, so the earnings window started on
the wrong day, the EOD report's day-cutoff excluded the whole afternoon, and —
worst — the risk engine's DAILY LOSS BUDGET reset at UTC midnight, 8 PM ET
(7 PM in winter). A safety rail with a hole in it every evening.

US equities and options trade on America/New_York time. That is a fact of the
VENUE, so the ZONE is pinned — deliberately hardcoded (D028, external-spec
constant): pinning "EDT" or a -4 offset instead would be wrong half the year;
the IANA zone flips EDT/EST by itself.

Storage stays UTC everywhere. These helpers exist only to answer two
questions correctly: "what calendar day is it AT THE MARKET?" and "what UTC
instant did that market day begin?" (for DB window queries against UTC
timestamps).

Windows note: python's zoneinfo needs the tzdata package there (in
backend/requirements.txt); Linux/macOS use the system database.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

# The venue's clock. External-spec constant (D028) — see module docstring.
MARKET_TZ = ZoneInfo("America/New_York")


def _require_aware(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError(
            "naive datetime passed to a market-time boundary — every KUBERA "
            "timestamp is tz-aware (AGENTS.md); attach the zone at the source"
        )
    return now


def market_today(now: datetime | None = None) -> date:
    """The calendar date at the market, right now (or at `now`).

    At 2026-08-18T03:11Z — 11:11 PM EDT on the 17th — this returns Aug 17,
    which is the answer the owner was owed."""
    return _require_aware(now).astimezone(MARKET_TZ).date()


def market_day_start_utc(now: datetime | None = None) -> datetime:
    """Midnight AT THE MARKET for the current market day, as a UTC instant.

    This is the boundary DB window queries want: rows stamped in UTC belong to
    the market day [market_day_start_utc, next one)."""
    d = market_today(now)
    start_local = datetime(d.year, d.month, d.day, tzinfo=MARKET_TZ)
    return start_local.astimezone(timezone.utc)
