"""T091b holding-period distribution — hand-computed from fixed timestamps.

Hand cases:
- buy 2026-01-05T14:00Z, sell 2026-01-05T20:00Z -> 6h = 0.25 days -> "hours"

T105/I020 split the old single "intraday" bucket into minutes / hours /
same_day. The owner's real record is 91 same-day option expiries out of 147
option fills, so for this account the informative split is BELOW a day: a
20-minute 0DTE scalp and a 7-hour hold are different behaviours, and the old
bucket called them the same thing.
Sub-day edges, hand-computed: 1/24 = 0.041666 (one hour),
6.5/24 = 0.270833 (one trading session).
- buy 2026-01-05, sell 2026-01-07                -> 2.0 days      -> "1-3d"
- buy 2026-01-05, sell 2026-01-15                -> 10.0 days     -> "1-2wk"
- buy 2026-01-05, sell 2026-03-05                -> 59.0 days     -> "over_1mo"
Boundaries are [lo, hi): exactly 1.0 day is "1-3d", exactly 4.0 is "1-2wk".
"""

import pytest

from analysis.attribution import (
    AttributedFill,
    fifo_attribution,
    hold_bucket,
    holding_period_distribution,
)


def buy(ts, qty=10, price=100.0, **tags):
    return AttributedFill("SPY", "buy", qty, price, ts, **tags)


def sell(ts, qty=10, price=110.0):
    return AttributedFill("SPY", "sell", qty, price, ts)


# --- bucket edges -------------------------------------------------------------

@pytest.mark.parametrize("days,expected", [
    (0.0, "minutes"), (0.04, "minutes"),          # under 1/24 = 0.041666
    (1 / 24, "hours"), (0.25, "hours"),           # 0.25 d = 6h, inside the session
    (6.5 / 24, "same_day"), (0.999, "same_day"),  # past a session, still same day
    (1.0, "1-3d"), (3.9, "1-3d"),
    (4.0, "1-2wk"), (14.9, "1-2wk"),
    (15.0, "2wk-1mo"), (30.9, "2wk-1mo"),
    (31.0, "over_1mo"), (400.0, "over_1mo"),
    (None, "unknown"),
])
def test_bucket_boundaries_are_half_open(days, expected):
    assert hold_bucket(days) == expected


# --- end-to-end through the FIFO engine --------------------------------------

def test_intraday_round_trip_measured_in_hours():
    """6 hours is 0.25 days — inside a session, so "hours", not "same_day"."""
    r = fifo_attribution([buy("2026-01-05T14:00:00Z"), sell("2026-01-05T20:00:00Z")])
    hp = r.holding_periods
    assert hp["by_bucket"]["hours"]["round_trips"] == 1
    assert hp["median_days"] == pytest.approx(0.25)
    assert hp["by_bucket"]["hours"]["win_rate"] == 1.0   # 100 -> 110
    assert hp["n_undated_round_trips"] == 0


def test_a_scalp_and_a_session_hold_are_no_longer_the_same_bucket():
    """The reason T105 split the bucket: these are different behaviours, and the
    old single 'intraday' label reported them identically."""
    scalp = fifo_attribution([buy("2026-01-05T14:00:00Z"), sell("2026-01-05T14:20:00Z")])
    held = fifo_attribution([buy("2026-01-05T09:30:00Z"), sell("2026-01-05T19:00:00Z")])
    assert "minutes" in scalp.holding_periods["by_bucket"]
    assert "same_day" in held.holding_periods["by_bucket"]


def test_multi_day_hold_lands_in_the_right_bucket():
    r = fifo_attribution([buy("2026-01-05T00:00:00Z"), sell("2026-01-07T00:00:00Z")])
    assert r.holding_periods["by_bucket"]["1-3d"]["round_trips"] == 1
    assert r.holding_periods["mean_days"] == pytest.approx(2.0)


def test_distribution_across_buckets_with_median():
    fills = [
        buy("2026-01-05T14:00:00Z"), sell("2026-01-05T20:00:00Z"),   # 0.25d
        buy("2026-02-01T00:00:00Z"), sell("2026-02-03T00:00:00Z"),   # 2d
        buy("2026-03-01T00:00:00Z"), sell("2026-03-11T00:00:00Z"),   # 10d
    ]
    hp = fifo_attribution(fills).holding_periods
    assert set(hp["by_bucket"]) == {"hours", "1-3d", "1-2wk"}   # 0.25d = 6h
    assert hp["n_dated_round_trips"] == 3
    assert hp["median_days"] == pytest.approx(2.0)      # middle of 0.25, 2, 10
    assert hp["shortest_days"] == pytest.approx(0.25)
    assert hp["longest_days"] == pytest.approx(10.0)
    assert "not a target" in hp["note"]


def test_partial_sells_produce_one_record_per_slice():
    """Two entries consumed by one sell = two round trips, each with its own
    clock — the slice really was held that long."""
    fills = [
        buy("2026-01-01T00:00:00Z", qty=5),
        buy("2026-01-10T00:00:00Z", qty=5),
        sell("2026-01-11T00:00:00Z", qty=10),
    ]
    hp = fifo_attribution(fills).holding_periods
    assert hp["n_dated_round_trips"] == 2
    assert hp["by_bucket"]["1-2wk"]["round_trips"] == 1     # 10 days
    assert hp["by_bucket"]["1-3d"]["round_trips"] == 1      # 1 day
    assert hp["longest_days"] == pytest.approx(10.0)


def test_losses_lower_the_bucket_win_rate():
    fills = [
        buy("2026-01-01T00:00:00Z", price=100.0),
        AttributedFill("SPY", "sell", 10, 90.0, "2026-01-02T00:00:00Z"),  # loss
        buy("2026-02-01T00:00:00Z", price=100.0),
        AttributedFill("SPY", "sell", 10, 120.0, "2026-02-02T00:00:00Z"),  # win
    ]
    slot = fifo_attribution(fills).holding_periods["by_bucket"]["1-3d"]
    assert slot["round_trips"] == 2 and slot["wins"] == 1
    assert slot["win_rate"] == 0.5
    assert slot["realized_pnl"] == pytest.approx(100.0)   # -100 + 200


# --- honesty on missing / corrupt clocks -------------------------------------

def test_undated_entry_is_counted_as_unknown_not_dropped():
    trips = [{"pnl": 5.0, "held_days": None}, {"pnl": 1.0, "held_days": 2.0}]
    hp = holding_period_distribution(trips)
    assert hp["by_bucket"]["unknown"]["round_trips"] == 1
    assert hp["n_undated_round_trips"] == 1
    assert hp["n_dated_round_trips"] == 1
    assert hp["median_days"] == pytest.approx(2.0)   # stats use dated trips only


def test_empty_history_is_calm():
    hp = holding_period_distribution([])
    assert hp["by_bucket"] == {} and hp["median_days"] is None
    assert hp["n_dated_round_trips"] == 0


def test_exit_before_entry_is_refused_not_negative():
    from analysis.attribution import _held_days
    assert _held_days("2026-01-10T00:00:00Z", "2026-01-01T00:00:00Z") is None
    assert _held_days("not-a-date", "2026-01-01T00:00:00Z") is None
    assert _held_days(None, "2026-01-01T00:00:00Z") is None


def test_naive_and_aware_timestamps_compare_safely():
    from analysis.attribution import _held_days
    assert _held_days("2026-01-01T00:00:00", "2026-01-03T00:00:00") == pytest.approx(2.0)
    assert _held_days("2026-01-01T00:00:00Z", "2026-01-03T00:00:00Z") == pytest.approx(2.0)
