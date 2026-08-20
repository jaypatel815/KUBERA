"""T063b — calibration v2, every number hand-computed in the comments."""

from datetime import datetime, timedelta, timezone

import pytest

from analysis.calibration import MIN_PER_BUCKET, compute_calibration
from data.models import DecisionJournal

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)
OLD = NOW - timedelta(days=30)          # every horizon below has passed


def _row(verdict="buy", conf=0.7, entry=100.0, target=None, stop=None,
         horizon=5, ts=OLD, followed=None, symbol="AAA"):
    return DecisionJournal(
        symbol=symbol, verdict=verdict, confidence=conf, thesis="t",
        horizon_days=horizon, entry_price=entry, target_price=target,
        stop_price=stop, ts=ts, followed=followed)


def _prices(mapping):
    return lambda sym: mapping.get(sym)


def test_confidence_curve_hand_computed():
    # Six buys stated at 0.70 (bucket 0.65-0.80): entries 100, four resolve
    # up (hit) and two down -> hit rate 4/6 = 0.6667, gap = 0.6667 - 0.70
    # = -0.0333 (slightly OVERconfident). Two more at 0.85: n=2 < 5 ->
    # listed, refused a rate.
    rows = [_row(conf=0.7, symbol=f"U{i}") for i in range(4)] + \
           [_row(conf=0.7, symbol=f"D{i}") for i in range(2)] + \
           [_row(conf=0.85, symbol=f"X{i}") for i in range(2)]
    px = _prices({**{f"U{i}": 110.0 for i in range(4)},
                  **{f"D{i}": 90.0 for i in range(2)},
                  **{f"X{i}": 110.0 for i in range(2)}})
    rep = compute_calibration(rows, px, now=NOW)

    assert rep.n_rows == 8 and rep.n_evaluable == 8
    b = {x.label: x for x in rep.buckets}
    mid = b["0.65-0.80"]
    assert (mid.n, mid.hits, mid.qualified) == (6, 4, True)
    assert mid.hit_rate == pytest.approx(4 / 6)
    assert mid.gap == pytest.approx(4 / 6 - 0.7)
    top = b["0.80+"]
    assert (top.n, top.qualified, top.hit_rate) == (2, False, None)  # named thin
    # weighted gap covers ONLY the qualified bucket
    assert rep.weighted_gap == pytest.approx(4 / 6 - 0.7)


def test_payoff_vs_plan_hand_computed():
    # Buy: entry 100, target 110, stop 95 -> planned R = 10/5 = 2.0;
    #      latest 108 -> realized R = 8/5 = 1.6.
    # Sell: entry 100, target 90, stop 104 -> planned R = 10/4 = 2.5;
    #      latest 92 -> realized R = -(92-100)/4 = 2.0.
    # Broken plan: buy with stop ABOVE entry -> invalid geometry, counted.
    rows = [
        _row(verdict="buy", entry=100, target=110, stop=95, symbol="B"),
        _row(verdict="sell", entry=100, target=90, stop=104, symbol="S"),
        _row(verdict="buy", entry=100, target=110, stop=105, symbol="BAD"),
    ]
    px = _prices({"B": 108.0, "S": 92.0, "BAD": 101.0})
    p = compute_calibration(rows, px, now=NOW).payoff
    assert (p["n_with_plan"], p["n_valid_geometry"], p["n_invalid_geometry"]) \
        == (3, 2, 1)
    assert p["avg_planned_r"] == pytest.approx((2.0 + 2.5) / 2)
    assert p["avg_realized_r"] == pytest.approx((1.6 + 2.0) / 2)
    assert "ENDPOINT-ONLY" in p["note"]


def test_override_versus_outcome():
    # Five overridden decisions ALL resolved as hits (KUBERA was right);
    # five followed resolved 2/5. override_rate = 5/10.
    rows = [_row(followed=False, symbol=f"O{i}") for i in range(5)] + \
           [_row(followed=True, symbol=f"FU{i}") for i in range(2)] + \
           [_row(followed=True, symbol=f"FD{i}") for i in range(3)]
    px = _prices({**{f"O{i}": 110.0 for i in range(5)},
                  **{f"FU{i}": 110.0 for i in range(2)},
                  **{f"FD{i}": 90.0 for i in range(3)}})
    o = compute_calibration(rows, px, now=NOW).override
    assert o["marked"] == 10 and o["override_rate"] == pytest.approx(0.5)
    assert o["overridden"] == {"n": 5, "hits": 5, "hit_rate": 1.0}
    assert o["followed"]["n"] == 5
    assert o["followed"]["hit_rate"] == pytest.approx(2 / 5)


def test_exclusions_are_counted_never_silent():
    rows = [
        _row(verdict="hold", symbol="H"),                 # no direction
        _row(entry=None, symbol="M"),                     # missing entry
        _row(ts=NOW, symbol="Y"),                         # too young
        _row(symbol="NOPX"),                              # no price
        _row(symbol="OK"),                                # the one evaluable
    ]
    rep = compute_calibration(rows, _prices({"OK": 110.0}), now=NOW)
    assert rep.n_rows == 5 and rep.n_evaluable == 1
    assert (rep.n_hold_excluded, rep.n_missing_fields,
            rep.n_too_young, rep.n_no_price) == (1, 1, 1, 1)


def test_empty_journal_reports_instead_of_raising():
    rep = compute_calibration([], price_lookup=None, now=NOW)
    assert rep.n_rows == 0 and rep.n_evaluable == 0
    assert rep.weighted_gap is None
    assert all(not b.qualified for b in rep.buckets)
    assert rep.payoff["avg_realized_r"] is None
    assert rep.override["override_rate"] is None
    assert rep.min_per_bucket == MIN_PER_BUCKET and rep.note
