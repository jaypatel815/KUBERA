"""T134 — the D021 evidence packet: what the Sept-12 revisit will be decided ON.

D021 (owner, 2026-08-13) deferred shorts/pairs/HRP ~30 days: "long-only
stands until paper DQS history proves discipline; revisit on evidence
(DQS trend, override rate, tier trips)." This script assembles exactly
those three, from what is actually persisted — and NAMES what isn't,
because a decision packet that quietly omits a metric is how a deferral
gets re-litigated on vibes.

    py scripts\\d021_evidence.py            # the packet, dated
    py scripts\\d021_evidence.py --since 2026-08-13

- DQS TREND: score_decisions over SignalLog, one 7-day window per week
  since the deferral date — the same scorer the brief uses, so the trend
  and the weekly review can never disagree.
- OVERRIDE RATE: compute_calibration's override×outcome split over the
  decision journal (marked decisions only; unmarked are counted and named).
- TIER TRIPS / BREAKER: risk_events (T135) — recording began 2026-08-20,
  and the packet SAYS so; days before that have no event history and
  nothing here pretends otherwise. Current tier and breaker state ride
  along from live risk state.

This packet RECOMMENDS NOTHING. D021 is the owner's decision; the packet's
job is to make it an informed one. Exit 0 informational / 2 not configured.
"""

import argparse
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from data.models import DecisionJournal, SignalLog  # noqa: E402
from data.risk_events import events_between  # noqa: E402
from risk.dqs import DQSReport, score_decisions  # noqa: E402

DEFAULT_DB = REPO_ROOT / "kubera.sqlite3"
D021_DATE = "2026-08-13"          # the deferral decision, on the record
EVENTS_SINCE = "2026-08-20"       # T135 recording began — earlier days have no history


def weekly_dqs(rows, since: date, until: date) -> list[tuple[str, DQSReport]]:
    """One DQS reading per 7-day window, week-ends stepping from `since`.
    Pure: caller supplies the rows."""
    out = []
    week_end = since + timedelta(days=7)
    while week_end <= until + timedelta(days=6):
        now = datetime.combine(min(week_end, until), time(23, 59),
                               tzinfo=timezone.utc)
        report = score_decisions(rows, window_days=7, now=now)
        out.append((min(week_end, until).isoformat(), report))
        week_end += timedelta(days=7)
    return out


def build_packet(session, since: date, today: date) -> list[str]:
    lines = [f"D021 EVIDENCE PACKET — generated {today.isoformat()} "
             f"(deferral {D021_DATE}, revisit ~2026-09-12)",
             "-" * 70]

    # 1. DQS trend
    rows = session.execute(select(SignalLog)).scalars().all()
    lines.append("1. DQS TREND (7-day windows, same scorer as the brief):")
    weeks = weekly_dqs(rows, since, today)
    if not any(r.orders for _, r in weeks):
        lines.append("   no orders in any window yet — the paper loop has "
                     "not traded since the deferral; a no-trade record IS "
                     "evidence of discipline, and it is also thin evidence")
    for week_end, r in weeks:
        lines.append(f"   week ending {week_end}: DQS {r.score:.0f} "
                     f"({r.orders} orders, {r.no_trades} no-trades)")

    # 2. Override rate
    jrows = session.execute(select(DecisionJournal)).scalars().all()
    since_dt = datetime.combine(since, time(0, 0), tzinfo=timezone.utc)
    jrows = [j for j in jrows
             if (j.ts if j.ts.tzinfo else j.ts.replace(tzinfo=timezone.utc))
             >= since_dt]
    lines.append("2. OVERRIDE RATE (decision journal since the deferral):")
    if not jrows:
        lines.append("   no journaled decisions since the deferral — the "
                     "override rate is UNKNOWN, not zero")
    else:
        from analysis.calibration import compute_calibration

        cal = compute_calibration(jrows, price_lookup=lambda s: None)
        ov = cal.override
        rate = ov.get("override_rate")
        rate_s = f"{rate:.0%}" if rate is not None else "unknown (none marked)"
        lines.append(f"   {len(jrows)} decision(s) journaled; override rate "
                     f"{rate_s}")
        for k in ("followed", "overridden"):
            if k in ov and isinstance(ov[k], dict):
                lines.append(f"   {k}: {ov[k]}")

    # 3. Tier / breaker history
    lines.append("3. TIER CHANGES + BREAKER TRIPS (risk_events, T135):")
    lines.append(f"   recording began {EVENTS_SINCE} — days before that "
                 "have NO event history; absence of earlier events is "
                 "absence of recording, not of incidents")
    try:
        evs = events_between(
            session,
            datetime.combine(since, time(0, 0), tzinfo=timezone.utc),
            datetime.combine(today, time(23, 59), tzinfo=timezone.utc))
    except OperationalError:
        lines.append("   risk_events table missing — run alembic upgrade "
                     "head; nothing is being recorded until then")
        evs = []
    trips = [e for e in evs if e.kind == "breaker_trip"]
    tiers = [e for e in evs if e.kind == "tier_change"]
    lines.append(f"   breaker trips recorded: {len(trips)}")
    for e in trips:
        lines.append(f"     {e.ts.date().isoformat()}: {e.detail[:90]}")
    lines.append(f"   tier observations recorded: {len(tiers)} "
                 "(first row is the starting tier, not a change)")
    for e in tiers:
        lines.append(f"     {e.ts.date().isoformat()}: {e.detail}")

    lines.append("-" * 70)
    lines.append("This packet recommends NOTHING (D021 is the owner's "
                 "call). The deferral text asked for these three metrics; "
                 "gaps above are named, never padded.")
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Assemble the D021 revisit evidence.")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--since", default=D021_DATE)
    args = ap.parse_args(argv)
    if not args.db.exists():
        print(f"NOT CONFIGURED — no database at {args.db}")
        return 2
    engine = create_engine(f"sqlite:///{args.db.as_posix()}")
    try:
        with sessionmaker(bind=engine)() as session:
            for line in build_packet(session,
                                     date.fromisoformat(args.since),
                                     date.today()):
                print(line)
        return 0
    except OperationalError as e:
        print(f"NOT CONFIGURED — {e.orig}; run alembic upgrade head")
        return 2
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
