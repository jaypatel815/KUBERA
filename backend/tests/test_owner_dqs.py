"""T067b — DQS v2 on the owner's own trips. Every penalty hand-computed."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from risk.owner_dqs import (
    FOMO_NOTE,
    MIN_TRIPS_PER_SIDE,
    budget_from_ips,
    disposition_effect,
    journal_discipline,
    revenge_sizing,
    score_owner_behavior,
)

T0 = datetime(2026, 3, 2, 14, 30, tzinfo=timezone.utc)


@dataclass
class Trip:
    pnl: float
    held_days: float | None
    exit_ts: str = ""


@dataclass
class Fill:
    """T069's sizing_drift reads `ts_iso` (a string), not `ts` — the shared
    contract, pinned here so a rename breaks this test loudly."""

    side: str
    ts_iso: str
    qty: float
    price: float


def trips(wins_hold, losses_hold):
    return ([Trip(pnl=100.0, held_days=h) for h in wins_hold]
            + [Trip(pnl=-100.0, held_days=h) for h in losses_hold])


# ------------------------------------------------- disposition effect

def test_cutting_winners_early_is_the_headline_case():
    """Winners median 1 day, losers median 4 days -> ratio 0.25;
    penalty = (1 - 0.25) * 60 = 45 -> capped at 30."""
    d = disposition_effect(trips([1, 1, 1, 1, 1], [4, 4, 4, 4, 4]))
    assert d["ratio"] == pytest.approx(0.25)
    assert d["penalty"] == 30.0
    assert "disposition effect" in d["reading"]


def test_mild_asymmetry_scores_between_the_bounds():
    """Winners 3, losers 4 -> ratio 0.75; penalty = 0.25 * 60 = 15.0."""
    d = disposition_effect(trips([3, 3, 3, 3, 3], [4, 4, 4, 4, 4]))
    assert d["penalty"] == pytest.approx(15.0)


def test_holding_winners_longer_is_free():
    d = disposition_effect(trips([9, 9, 9, 9, 9], [2, 2, 2, 2, 2]))
    assert d["penalty"] == 0.0 and d["ratio"] > 1
    assert "no cut-winners signature" in d["reading"]


def test_refuses_under_the_sample_floor():
    d = disposition_effect(trips([1] * (MIN_TRIPS_PER_SIDE - 1), [4] * 9))
    assert d["penalty"] == 0.0 and d["ratio"] is None
    assert "insufficient sample" in d["why"]


def test_undated_and_negative_holds_are_skipped_not_defaulted():
    rows = trips([1, 1, 1, 1, 1], [4, 4, 4, 4, 4]) + [
        Trip(pnl=50.0, held_days=None),      # undated lot
        Trip(pnl=50.0, held_days=-3.0),      # corrupt clock
        Trip(pnl=0.0, held_days=2.0),        # scratch: neither win nor loss
    ]
    d = disposition_effect(rows)
    assert d["winners"] == 5 and d["losers"] == 5


def test_same_session_losers_give_no_verdict():
    d = disposition_effect(trips([0.2] * 5, [0.0] * 5))
    assert d["penalty"] == 0.0 and d["ratio"] is None
    assert "same-session" in d["why"]


# ------------------------------------------------------ revenge sizing

def test_revenge_sizing_reuses_t069_and_scores_the_ratio():
    """3 losses then a $2,000 buy each; 3 wins then a $1,000 buy each ->
    ratio 2.0 -> penalty = (2.0 - 1) * 30 = 30 (the cap)."""
    trip_rows, fill_rows = [], []
    for i in range(3):
        exit_ts = T0 + timedelta(days=i)
        trip_rows.append(Trip(pnl=-50.0, held_days=1.0, exit_ts=exit_ts.isoformat()))
        fill_rows.append(Fill("buy", (exit_ts + timedelta(minutes=30)).isoformat(),
                              20, 100.0))          # $2,000 after each loss
    for i in range(3, 6):
        exit_ts = T0 + timedelta(days=i)
        trip_rows.append(Trip(pnl=50.0, held_days=1.0, exit_ts=exit_ts.isoformat()))
        fill_rows.append(Fill("buy", (exit_ts + timedelta(minutes=30)).isoformat(),
                              10, 100.0))          # $1,000 after each win
    r = revenge_sizing(trip_rows, fill_rows)
    assert r["ratio"] == pytest.approx(2.0)
    assert r["penalty"] == 30.0
    assert "revenge signature" in r["reading"]
    assert "T069" in r["source"]


def test_revenge_sizing_refuses_without_paired_observations():
    r = revenge_sizing([], [])
    assert r["penalty"] == 0.0 and r["ratio"] is None and "insufficient" in r["why"]


# --------------------------------------------------- journal discipline

def test_unmarked_decisions_cost_overrides_do_not():
    """10 decisions, 5 unmarked -> 0.5 * 20 = 10.0. Overrides never appear."""
    j = journal_discipline(total=10, unmarked=5)
    assert j["penalty"] == pytest.approx(10.0)
    assert j["unmarked_frac"] == 0.5
    j2 = journal_discipline(total=10, unmarked=0)
    assert j2["penalty"] == 0.0


def test_journal_refuses_under_the_floor():
    j = journal_discipline(total=2, unmarked=2)
    assert j["penalty"] == 0.0 and "fewer than" in j["why"]


# ------------------------------------------------------ IPS budget

def test_ips_budget_is_a_proposal_and_flags_disagreement():
    """15% tolerable drawdown / 3 = 5% implied daily; engine enforces 2%."""
    b = budget_from_ips(0.15, 0.02)
    assert b["implied_daily_loss_frac"] == pytest.approx(0.05)
    assert b["agrees"] is False
    assert "looser" in b["reading"]
    assert "PROPOSAL ONLY" in b["note"]


def test_ips_budget_agrees_within_tolerance_and_needs_an_ips():
    assert budget_from_ips(0.06, 0.02)["agrees"] is True
    assert budget_from_ips(None, 0.02) is None
    assert budget_from_ips(0.0, 0.02) is None


# ------------------------------------------------------------- report

def test_full_report_sums_capped_penalties_and_names_the_fomo_gap():
    """disposition 30 (capped) + journal 10 + revenge 0 (unmeasurable)
    -> 100 - 40 = 60.0."""
    r = score_owner_behavior(
        trips([1] * 5, [4] * 5), [],
        journal_total=10, journal_unmarked=5,
        ips_max_drawdown_frac=0.15, enforced_daily_loss_frac=0.02,
    )
    assert r.score == pytest.approx(60.0)
    assert r.trips_scored == 10
    assert r.fomo_note == FOMO_NOTE and "date-only" in r.fomo_note
    assert r.ips_budget["agrees"] is False
    assert any("partial read" in n for n in r.notes)


def test_empty_record_is_100_by_absence_and_says_so():
    r = score_owner_behavior([], [])
    assert r.score == 100.0
    assert any("absence of evidence" in n for n in r.notes)
    assert r.ips_budget is None
