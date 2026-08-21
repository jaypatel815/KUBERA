"""T153 — payoff planner: hand-computed schedules, strategy divergence,
named refusals. The 11-month case is worked by hand in comments."""

import pytest

from analysis.payoff import (
    DebtSpec,
    PayoffImpossible,
    build_plan,
    compare_strategies,
)


def test_zero_apr_is_plain_division():
    # $100 at 0%, $50/mo -> exactly 2 months, zero interest
    p = build_plan([DebtSpec("card", 100.0, 0.0, 50.0)])
    assert p.months == 2
    assert p.total_interest == 0.0
    assert p.total_paid == pytest.approx(100.0)


def test_single_debt_hand_computed_eleven_months():
    # $1,000 at 12% APR (1%/mo), $100/mo:
    #   m1: +10.00 -> 910.00      m2: +9.10 -> 819.10   m3: +8.19 -> 727.29
    #   m4: +7.27 -> 634.56       m5: +6.35 -> 540.91   m6: +5.41 -> 446.32
    #   m7: +4.46 -> 350.78       m8: +3.51 -> 254.29   m9: +2.54 -> 156.83
    #   m10:+1.57 -> 58.40        m11:+0.58 -> pay 58.98, done
    # total interest = 58.98; total paid = 1,058.98
    p = build_plan([DebtSpec("visa", 1000.0, 0.12, 100.0)])
    assert p.months == 11
    assert p.total_interest == pytest.approx(58.98, abs=0.02)
    assert p.total_paid == pytest.approx(1058.98, abs=0.02)
    assert p.outcomes[0].payoff_month == 11


def test_avalanche_and_snowball_pick_different_first_targets():
    # A: big balance, high APR. B: small balance, low APR.
    debts = [DebtSpec("A-highAPR", 2000.0, 0.30, 40.0),
             DebtSpec("B-small", 500.0, 0.06, 15.0)]
    av = build_plan(debts, extra_monthly=100.0, strategy="avalanche")
    sn = build_plan(debts, extra_monthly=100.0, strategy="snowball")
    first_av = min(av.outcomes, key=lambda o: o.payoff_month).name
    first_sn = min(sn.outcomes, key=lambda o: o.payoff_month).name
    assert first_av == "A-highAPR" and first_sn == "B-small"
    # mathematical truth: same cash, better aim -> avalanche never pays more
    assert av.total_interest <= sn.total_interest


def test_compare_reports_the_honest_delta_and_leaves_the_choice():
    debts = [DebtSpec("A", 2000.0, 0.30, 40.0), DebtSpec("B", 500.0, 0.06, 15.0)]
    c = compare_strategies(debts, extra_monthly=100.0)
    assert c["interest_saved_by_avalanche"] == pytest.approx(
        c["snowball"].total_interest - c["avalanche"].total_interest, abs=0.01)
    assert "yours" in c["note"]  # the decision is the owner's, stated


def test_impossible_plan_is_refused_with_names_not_an_infinite_loop():
    # $1,000 at 60% APR accrues $50/mo; a $30 minimum never wins
    with pytest.raises(PayoffImpossible, match="outrun interest"):
        build_plan([DebtSpec("payday", 1000.0, 0.60, 30.0)])


def test_freed_minimum_rolls_and_accelerates_the_next_debt():
    debts = [DebtSpec("small", 100.0, 0.0, 50.0),   # closes month 2
             DebtSpec("big", 1000.0, 0.0, 50.0)]
    p = build_plan(debts)
    # months 1-2: big pays 50+50=100 -> 900. From month 3 the freed $50
    # rolls: big pays 100/mo -> 900/100 = 9 more months -> month 11.
    assert min(o.payoff_month for o in p.outcomes) == 2
    assert p.months == 11


def test_debt_free_is_an_answer_not_an_error():
    p = build_plan([])
    assert p.months == 0 and "debt-free" in p.note
