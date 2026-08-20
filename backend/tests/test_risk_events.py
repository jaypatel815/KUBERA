"""T135 + T134 — risk-event history and the D021 evidence packet: dedupe
proven, the packet's gaps NAMED on empty fixtures, weekly DQS windowing
hand-checked. History only exists if something writes it down."""

import importlib.util
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from test_paper_loop import db  # noqa: F401

from data.models import RiskEvent, SignalLog
from data.risk_events import (
    BREAKER_TRIP,
    TIER_CHANGE,
    events_between,
    observe_breaker,
    observe_tier,
)

SCRIPT = (Path(__file__).resolve().parents[2] / "scripts" /
          "d021_evidence.py")
spec = importlib.util.spec_from_file_location("d021_evidence_t134", SCRIPT)
assert spec is not None and spec.loader is not None
d021 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d021)


def test_tier_observation_dedupes_by_level(db):  # noqa: F811
    assert observe_tier(db, 0, "full") is not None      # starting tier
    assert observe_tier(db, 0, "full") is None          # unchanged -> no row
    assert observe_tier(db, 1, "reduced") is not None   # change -> row
    assert observe_tier(db, 0, "full") is not None      # change back -> row
    kinds = [e.kind for e in db.query(RiskEvent).all()]
    assert kinds == [TIER_CHANGE] * 3


def test_breaker_observation_dedupes_by_reason(db):  # noqa: F811
    assert observe_breaker(db, False, None) is None       # not tripped
    assert observe_breaker(db, True, "trip A") is not None
    assert observe_breaker(db, True, "trip A") is None    # same trip, seen again
    assert observe_breaker(db, True, "trip B") is not None  # a NEW trip
    assert len(db.query(RiskEvent).filter_by(kind=BREAKER_TRIP).all()) == 2


def test_events_between_bounds(db):  # noqa: F811
    observe_tier(db, 0, "full")
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    end = datetime.now(timezone.utc) + timedelta(hours=1)
    assert len(events_between(db, start, end)) == 1
    assert events_between(db, end, end + timedelta(hours=1)) == []


def test_packet_names_every_gap_on_thin_data(db):  # noqa: F811
    lines = d021.build_packet(db, date(2026, 8, 13), date(2026, 8, 27))
    text = "\n".join(lines)
    assert "no orders in any window yet" in text
    assert "UNKNOWN, not zero" in text                 # override gap named
    assert "recording began 2026-08-20" in text        # history gap named
    assert "recommends NOTHING" in text
    assert "revisit ~2026-09-12" in text


def test_packet_weekly_dqs_windows_and_events(db):  # noqa: F811
    # two orders in week 1, none later; one breaker trip on the record
    base = datetime(2026, 8, 14, 15, 0, tzinfo=timezone.utc)
    for i in range(2):
        db.add(SignalLog(
            ts=base + timedelta(hours=i), strategy="momentum", symbol="SPY",
            signal_weight=1.0, equity=10_000.0, current_value=0.0,
            target_value=500.0, action="ordered",
            bars_asof=base, source="t"))
    db.commit()
    observe_breaker(db, True, "daily loss circuit breaker: test trip")
    lines = d021.build_packet(db, date(2026, 8, 13), date(2026, 8, 27))
    text = "\n".join(lines)
    assert "week ending 2026-08-20" in text and "week ending 2026-08-27" in text
    assert "2 orders" in text
    assert "breaker trips recorded: 1" in text
    assert "test trip" in text
