"""T137 — the EDGAR backfill: hint derivation hand-checked against real
clock boundaries, idempotency proven (a second run changes zero rows),
failures named per symbol. sec.gov is unreachable from the sandbox, so the
client is always a fake here — the live run is the owner's."""

import importlib.util
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from test_paper_loop import db  # noqa: F401

from data.models import EarningsObserved

SCRIPT = (Path(__file__).resolve().parents[2] / "scripts" /
          "earnings_backfill.py")
spec = importlib.util.spec_from_file_location("earnings_backfill_t137", SCRIPT)
assert spec is not None and spec.loader is not None
bf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bf)


def test_hint_from_real_acceptance_clocks():
    # 08:00 ET = 12:00 UTC in August (EDT) -> before the open
    assert bf.hint_from_acceptance(
        datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)) == "bmo"
    # 16:05 ET -> after the close
    assert bf.hint_from_acceptance(
        datetime(2026, 8, 20, 20, 5, tzinfo=timezone.utc)) == "amc"
    # 10:30 ET -> during the session (rare, real, worth labeling)
    assert bf.hint_from_acceptance(
        datetime(2026, 8, 20, 14, 30, tzinfo=timezone.utc)) == "during"
    # EDGAR omitted the clock: None, never a guess
    assert bf.hint_from_acceptance(None) is None
    # boundary: exactly 09:30 ET is NOT before the open
    assert bf.hint_from_acceptance(
        datetime(2026, 8, 20, 13, 30, tzinfo=timezone.utc)) == "during"


class FakeEdgar:
    def __init__(self, filings):
        self._filings = filings

    def earnings_history(self, symbol):
        return SimpleNamespace(symbol=symbol.upper(), cik=320193,
                               filings=self._filings, unparsed=[])


def _filing(day, hour_utc=20):
    return SimpleNamespace(
        symbol="AAPL", filing_date=date(2026, 8, day),
        acceptance_utc=datetime(2026, 8, day, hour_utc, 30,
                                tzinfo=timezone.utc),
        items="2.02")


def test_backfill_upserts_and_is_idempotent(db):  # noqa: F811
    edgar = FakeEdgar([_filing(1), _filing(2, hour_utc=12)])
    changed, seen = bf.backfill_symbol(db, edgar, "AAPL")
    assert (changed, seen) == (2, 2)
    rows = db.query(EarningsObserved).order_by(
        EarningsObserved.event_date).all()
    assert [r.event_date for r in rows] == ["2026-08-01", "2026-08-02"]
    assert rows[0].time_hint == "amc" and rows[1].time_hint == "bmo"
    assert all(r.source == "edgar-backfill" for r in rows)
    assert all(r.eps_actual is None for r in rows)  # EDGAR has no estimates

    # run two: nothing changes — re-running is always safe
    changed2, seen2 = bf.backfill_symbol(db, edgar, "AAPL")
    assert (changed2, seen2) == (0, 2)
    assert db.query(EarningsObserved).count() == 2


def test_backfill_never_overwrites_richer_rows(db):  # noqa: F811
    # a row that FMP already enriched with eps keeps its data — the store's
    # own upsert semantics, exercised through the backfill path
    db.add(EarningsObserved(symbol="AAPL", event_date="2026-08-01",
                            time_hint="amc", eps_actual=1.23,
                            source="fmp-free"))
    db.commit()
    edgar = FakeEdgar([_filing(1)])
    changed, seen = bf.backfill_symbol(db, edgar, "AAPL")
    row = db.query(EarningsObserved).one()
    assert row.eps_actual == 1.23          # enrichment survived
    assert row.source == "fmp-free"        # provenance survived
    assert seen == 1
