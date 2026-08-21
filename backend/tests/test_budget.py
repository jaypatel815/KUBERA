"""T154 — budget + utilization engine. Every expected number computed by
hand in the comments; the engine must agree with the pencil."""

from datetime import date

import pytest

from analysis.budget import (
    UTILIZATION_CAUTION_FRAC,
    BudgetError,
    CardSpec,
    DueSpec,
    FlowSpec,
    SpendSpec,
    bills_due_within,
    card_utilization,
    month_view,
    next_due_date,
)

FLOWS = [
    FlowSpec("salary", "income", 5000.0, "salary"),
    FlowSpec("rent", "expense", 1500.0, "housing"),
    FlowSpec("netflix", "expense", 100.0, "subscriptions"),
]
SPENDS = [
    SpendSpec("2026-08-03", 200.50, "groceries"),
    SpendSpec("2026-08-10", 89.50, "dining"),
    SpendSpec("2026-08-15", 110.00, "groceries"),
    SpendSpec("2026-07-30", 999.00, "groceries"),  # outside the month
]


def test_month_view_hand_computed():
    # income 5000; recurring 1500+100=1600; actual in Aug = 200.50+89.50+110
    # = 400.00; leftover = 5000-1600-400 = 3000.00
    v = month_view(FLOWS, SPENDS, "2026-08", today=date(2026, 8, 16))
    assert v["income_planned"] == 5000.0
    assert v["recurring_expense_planned"] == 1600.0
    assert v["recurring_expense_by_category"] == {
        "housing": 1500.0, "subscriptions": 100.0}
    assert v["actual_total"] == 400.0
    assert v["actual_by_category"] == {"groceries": 310.50, "dining": 89.50}
    assert v["leftover"] == 3000.0
    # categories ordered by spend, biggest first
    assert list(v["actual_by_category"]) == ["groceries", "dining"]


def test_month_view_pace_hand_computed():
    # Aug has 31 days; on the 16th elapsed = 16/31 = 0.5161
    # discretionary = 5000-1600 = 3400; to-date budget = 3400*16/31 = 1754.84
    # headroom = 1754.84-400 = 1354.84 -> under pace
    v = month_view(FLOWS, SPENDS, "2026-08", today=date(2026, 8, 16))
    p = v["pace"]
    assert p["elapsed_frac"] == round(16 / 31, 4)
    assert p["discretionary_budget"] == 3400.0
    assert p["budget_to_date"] == 1754.84
    assert p["headroom_to_date"] == 1354.84
    assert p["over_pace"] is False


def test_month_view_past_and_future_months_elapsed_frac():
    past = month_view(FLOWS, SPENDS, "2026-07", today=date(2026, 8, 16))
    assert past["pace"]["elapsed_frac"] == 1.0
    assert past["actual_total"] == 999.0  # the July entry counts there
    future = month_view(FLOWS, [], "2026-09", today=date(2026, 8, 16))
    assert future["pace"]["elapsed_frac"] == 0.0
    assert future["pace"]["over_pace"] is False  # 0 spent vs 0 budget-to-date


def test_month_view_empty_is_honest_not_zero_division():
    v = month_view([], [], "2026-08", today=date(2026, 8, 16))
    assert v["leftover"] == 0.0
    assert v["pace"]["discretionary_budget"] == 0.0
    assert any("no recurring flows" in n for n in v["notes"])
    # the double-count hazard is named for every caller
    assert any("double-counted" in n for n in v["notes"])


def test_month_view_refuses_malformed_month():
    for bad in ("2026/08", "aug 2026", "2026-13", "", "2026-8-1"):
        with pytest.raises(BudgetError):
            month_view([], [], bad)


def test_card_utilization_caution_line_is_strict():
    # 300/1000 = 0.30 exactly -> NOT above; 301/1000 -> above
    out = card_utilization([
        CardSpec("At the line", 300.0, 1000.0, "2026-08-20"),
        CardSpec("Over", 301.0, 1000.0, "2026-08-20"),
    ])
    by_name = {c["name"]: c for c in out["cards"]}
    assert by_name["At the line"]["above_caution"] is False
    assert by_name["Over"]["above_caution"] is True
    assert out["any_above_caution"] is True
    assert out["caution_line_frac"] == UTILIZATION_CAUTION_FRAC
    # sorted highest utilization first
    assert out["cards"][0]["name"] == "Over"
    # overall: (300+301)/(1000+1000) = 0.3005
    assert out["overall_utilization_frac"] == 0.3005


def test_card_utilization_no_limit_named_never_guessed():
    out = card_utilization([CardSpec("Mystery", 500.0, None, "2026-08-20")])
    assert out["cards"] == []
    assert out["no_limit_stated"] == ["Mystery"]
    assert out["overall_utilization_frac"] is None


def test_next_due_date_month_and_year_boundaries():
    # today the 21st: due 25 -> this month; due 3 -> next month
    assert next_due_date(25, date(2026, 8, 21)) == date(2026, 8, 25)
    assert next_due_date(3, date(2026, 8, 21)) == date(2026, 9, 3)
    # due today counts as today, not next month
    assert next_due_date(21, date(2026, 8, 21)) == date(2026, 8, 21)
    # December wraps the year
    assert next_due_date(2, date(2026, 12, 30)) == date(2027, 1, 2)
    with pytest.raises(BudgetError):
        next_due_date(29, date(2026, 8, 21))


def test_bills_due_within_horizon_sorted_soonest_first():
    dues = [
        DueSpec("Visa", 25, 35.0),       # 4 days out
        DueSpec("Car loan", 3, 220.0),   # 13 days out -> excluded at 7
        DueSpec("Store card", 21, 40.0),  # today
    ]
    out = bills_due_within(dues, today=date(2026, 8, 21), horizon_days=7)
    assert [b["name"] for b in out] == ["Store card", "Visa"]
    assert out[0]["days_until"] == 0
    assert out[1] == {"name": "Visa", "due_date": "2026-08-25",
                      "days_until": 4, "min_payment": 35.0}
