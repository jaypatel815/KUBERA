"""T076b — FOMC published-schedule table + priced-for-perfection flag."""

from datetime import date, timedelta

import pytest

from analysis.events import entry_guard, upcoming_events
from analysis.fomc import (
    FOMC_DECISION_DATES,
    FOMC_NAME,
    STALE_WARN_DAYS,
    fomc_staleness_note,
    priced_for_perfection,
    with_fomc,
)


def test_table_is_sane():
    """Sixteen decision days, strictly ascending, all valid ISO dates,
    roughly eight per year — the published cadence."""
    parsed = [date.fromisoformat(d) for d in FOMC_DECISION_DATES]
    assert len(parsed) == 16
    assert parsed == sorted(parsed)
    assert sum(1 for d in parsed if d.year == 2026) == 8
    assert sum(1 for d in parsed if d.year == 2027) == 8


def test_with_fomc_merges_without_mutating():
    fred_cal = {"CPI": ["2026-09-11"]}
    merged = with_fomc(fred_cal)
    assert merged["CPI"] == ["2026-09-11"]
    assert merged[FOMC_NAME] == list(FOMC_DECISION_DATES)
    assert FOMC_NAME not in fred_cal                    # input untouched
    assert with_fomc(None) == {FOMC_NAME: list(FOMC_DECISION_DATES)}


def test_fomc_guards_entries_like_any_release():
    """The day before the 2026-09-16 decision: entry_guard names it."""
    reasons = entry_guard(with_fomc(None), date(2026, 9, 15), window_before=1)
    assert any(FOMC_NAME in r and "2026-09-16" in r for r in reasons)
    clear = entry_guard(with_fomc(None), date(2026, 9, 1), window_before=1)
    assert clear == []


def test_fomc_appears_in_upcoming_events():
    evs = upcoming_events(with_fomc(None), date(2026, 9, 10), horizon_days=14)
    assert any(e.name == FOMC_NAME and e.date == "2026-09-16" for e in evs)


def test_staleness_note_ladder():
    last = date.fromisoformat(FOMC_DECISION_DATES[-1])
    assert fomc_staleness_note(last - timedelta(days=STALE_WARN_DAYS + 30)) is None
    warn = fomc_staleness_note(last - timedelta(days=10))
    assert warn is not None and "append" in warn
    dead = fomc_staleness_note(last + timedelta(days=1))
    assert dead is not None and "EXHAUSTED" in dead


def test_priced_for_perfection_hand_computed():
    """Runup 6% vs p95 5% -> flag True; 3% vs 5% -> False; missing -> None."""
    hot = priced_for_perfection(0.06, 0.05)
    assert hot["flag"] is True and "perfection" in hot["note"]
    assert hot["runup_5d_frac"] == pytest.approx(0.06)
    cool = priced_for_perfection(0.03, 0.05)
    assert cool["flag"] is False
    assert priced_for_perfection(None, 0.05) is None
    assert priced_for_perfection(0.06, None) is None
    assert priced_for_perfection(0.06, 0.0) is None     # degenerate p95
