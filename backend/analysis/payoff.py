"""T153 (D039 Phase 9) — debt payoff planning: avalanche vs snowball.

Deterministic simulation, month by month, standard consumer-debt arithmetic:
interest accrues at apr_frac/12 on the running balance, every open debt gets
its minimum, and the EXTRA dollars go to one target — highest APR first
(avalanche) or lowest balance first (snowball). When a debt closes, its
freed minimum rolls into the extra pool (that rolling is the whole point of
the snowball method, and avalanche gets it too so the comparison is fair).

Honesty rails:
- A plan whose payments cannot outrun interest is REFUSED with the debt and
  the shortfall named — an infinite schedule presented as a plan is a lie.
- The horizon is capped at 100 years; anything longer is refused, not drawn.
- This describes arithmetic on stated balances and APRs. It is not tax,
  bankruptcy, or credit advice, and the payload says so.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MONTHS_CAP = 1200  # 100 years — beyond this a "plan" is not a plan
STRATEGIES = ("avalanche", "snowball")


class PayoffImpossible(ValueError):
    """Named refusal: the stated payments never retire the stated balance."""


@dataclass
class _Live:
    """A debt mid-simulation — mutable on purpose, module-private."""

    name: str
    balance: float
    apr_frac: float
    min_payment: float
    interest_paid: float = 0.0


@dataclass(frozen=True)
class DebtSpec:
    name: str
    balance: float
    apr_frac: float
    min_payment: float


@dataclass(frozen=True)
class DebtOutcome:
    name: str
    payoff_month: int          # 1-based month in which the balance hits zero
    interest_paid: float


@dataclass(frozen=True)
class PayoffPlan:
    strategy: str
    months: int
    total_interest: float
    total_paid: float
    monthly_commitment: float  # sum of minimums + extra, at the start
    outcomes: list[DebtOutcome] = field(default_factory=list)
    note: str = ("arithmetic on stated balances and APRs — not tax or "
                 "credit advice; freed minimums roll into the extra pool")


def _target(open_debts: list[_Live], strategy: str) -> _Live:
    if strategy == "avalanche":
        return max(open_debts, key=lambda r: (r.apr_frac, r.balance))
    return min(open_debts, key=lambda r: (r.balance, -r.apr_frac))


def build_plan(debts: list[DebtSpec], extra_monthly: float = 0.0,
               strategy: str = "avalanche") -> PayoffPlan:
    if strategy not in STRATEGIES:
        raise ValueError(f"strategy must be one of {STRATEGIES}, got {strategy!r}")
    if extra_monthly < 0:
        raise ValueError(f"extra_monthly cannot be negative ({extra_monthly})")
    live = [_Live(d.name, d.balance, d.apr_frac, d.min_payment)
            for d in debts if d.balance > 0]
    commitment = sum(d.min_payment for d in debts if d.balance > 0) + extra_monthly
    if not live:
        return PayoffPlan(strategy=strategy, months=0, total_interest=0.0,
                          total_paid=0.0, monthly_commitment=commitment,
                          outcomes=[], note="debt-free — nothing to plan")

    outcomes: list[DebtOutcome] = []
    total_paid = 0.0
    extra_pool = extra_monthly
    month = 0
    while live:
        month += 1
        if month > MONTHS_CAP:
            raise PayoffImpossible(
                f"payoff exceeds {MONTHS_CAP // 12} years — the stated "
                "payments barely outrun interest; this is not a plan")
        # 1) accrue
        for row in live:
            interest = row.balance * row.apr_frac / 12.0
            row.balance += interest
            row.interest_paid += interest
        # 2) minimums
        for row in live:
            pay = min(row.min_payment, row.balance)
            row.balance -= pay
            total_paid += pay
        # 3) extra to the strategy's target (and cascade to the next target
        #    within the same month if the extra overshoots a small balance)
        remaining_extra = extra_pool
        while remaining_extra > 1e-9 and any(r.balance > 1e-9 for r in live):
            t = _target([r for r in live if r.balance > 1e-9], strategy)
            pay = min(remaining_extra, t.balance)
            t.balance -= pay
            total_paid += pay
            remaining_extra -= pay
        # 4) close finished debts; their minimums roll into the pool
        still: list[_Live] = []
        for row in live:
            if row.balance <= 1e-9:
                outcomes.append(DebtOutcome(name=row.name, payoff_month=month,
                                            interest_paid=round(row.interest_paid, 2)))
                extra_pool += row.min_payment
            else:
                still.append(row)
        # 5) progress check: payments must outrun interest or the schedule
        #    is infinite — refuse NOW with names, not at the horizon cap
        if still:
            paying = sum(r.min_payment for r in still) + extra_pool
            worst = max(still,
                        key=lambda r: r.balance * r.apr_frac / 12.0 - r.min_payment)
            if paying <= sum(r.balance * r.apr_frac / 12.0 for r in still) + 1e-9:
                raise PayoffImpossible(
                    f"payments (${paying:,.2f}/mo) do not outrun interest "
                    f"(worst: {worst.name} accrues "
                    f"${worst.balance * worst.apr_frac / 12.0:,.2f}/mo against "
                    f"its ${worst.min_payment:,.2f} minimum) — increase "
                    "the payment or this balance never reaches zero")
        live = still

    total_interest = round(sum(o.interest_paid for o in outcomes), 2)
    return PayoffPlan(strategy=strategy, months=month,
                      total_interest=total_interest,
                      total_paid=round(total_paid, 2),
                      monthly_commitment=round(commitment, 2),
                      outcomes=outcomes)


def compare_strategies(debts: list[DebtSpec],
                       extra_monthly: float = 0.0) -> dict:
    """Both plans + the honest delta. Avalanche never pays MORE interest
    than snowball (same cash, better-aimed); snowball's case is morale —
    said in the payload, decided by the owner."""
    av = build_plan(debts, extra_monthly, "avalanche")
    sn = build_plan(debts, extra_monthly, "snowball")
    return {
        "avalanche": av,
        "snowball": sn,
        "interest_saved_by_avalanche": round(sn.total_interest - av.total_interest, 2),
        "months_difference": sn.months - av.months,
        "note": ("avalanche minimizes interest; snowball buys earlier "
                 "small wins — which one YOU stick with is the real "
                 "variable, and that choice is yours"),
    }
