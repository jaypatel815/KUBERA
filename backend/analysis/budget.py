"""T154 (D039 Phase 9) — budget + utilization engine. Pure and tested.

Month view of income vs planned recurring vs actual spending by category,
leftover, budget pace, per-card utilization against the 30% caution line,
and next-due-date math for bills. No DB access here — callers pass plain
specs; the store (data/household.py) keeps the facts.

Conventions, stated because money math never gets to be implicit:
- A month is "YYYY-MM". Spending entries are filtered to it by date prefix.
- Recurring flows are MONTHLY (v1 — weekly paychecks need doubling by hand
  until a cadence ticket earns its place; recorded in Batch #14's manifest).
- leftover = planned income − planned recurring expenses − actual logged
  spending. If the owner ALSO logs a bill that is already a recurring flow,
  it is double-counted — the payload's note names this hazard rather than
  guessing which entries are duplicates.
- Budget pace compares actual spending to the pro-rata share of the
  DISCRETIONARY budget (income − recurring). Past months read as fully
  elapsed, future months as not started.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

# The widely-cited credit-utilization caution threshold. Fixed by external
# convention (credit-score guidance), not tunable — crossing it is the fact
# the owner asked the dashboard to surface.
UTILIZATION_CAUTION_FRAC = 0.30


class BudgetError(ValueError):
    """Named refusal — malformed month strings or specs never compute."""


@dataclass(frozen=True)
class FlowSpec:
    """One recurring monthly flow, as stated by the owner."""

    name: str
    direction: str  # "income" | "expense"
    amount: float
    category: str = "uncategorized"


@dataclass(frozen=True)
class SpendSpec:
    """One logged spend (manual or CSV-imported)."""

    date: str  # ISO YYYY-MM-DD
    amount: float
    category: str = "uncategorized"


@dataclass(frozen=True)
class CardSpec:
    """A credit card as stored: balance + limit + the date the owner stated it."""

    name: str
    balance: float
    credit_limit: float | None
    balance_asof: str


@dataclass(frozen=True)
class DueSpec:
    """A debt with a payment due day (1..28, enforced by the store)."""

    name: str
    due_day: int
    min_payment: float


def _check_month(month: str) -> tuple[int, int]:
    try:
        year_s, mon_s = month.split("-")
        year, mon = int(year_s), int(mon_s)
        if not (1 <= mon <= 12) or year < 1970:
            raise ValueError
    except (ValueError, AttributeError):
        raise BudgetError(
            f"month must be 'YYYY-MM', got {month!r}") from None
    return year, mon


def month_view(flows: list[FlowSpec], spends: list[SpendSpec], month: str,
               today: date | None = None) -> dict:
    """Income vs planned recurring vs actual spending for one month.

    Every figure is computed here, deterministically; the conversation layer
    narrates, it never re-derives.
    """
    year, mon = _check_month(month)
    today = today or date.today()
    days_in_month = calendar.monthrange(year, mon)[1]

    income_planned = round(sum(
        f.amount for f in flows if f.direction == "income"), 2)
    recurring_expense: dict[str, float] = {}
    for f in flows:
        if f.direction == "expense":
            cat = (f.category or "uncategorized").strip().lower()
            recurring_expense[cat] = recurring_expense.get(cat, 0.0) + f.amount
    recurring_expense_planned = round(sum(recurring_expense.values()), 2)

    actual_by_category: dict[str, float] = {}
    for s in spends:
        if s.date.startswith(month + "-"):
            cat = (s.category or "uncategorized").strip().lower()
            actual_by_category[cat] = actual_by_category.get(cat, 0.0) + s.amount
    actual_total = round(sum(actual_by_category.values()), 2)

    leftover = round(income_planned - recurring_expense_planned - actual_total, 2)

    # Pace: how far through the month vs how much of the discretionary
    # budget is spent. A month in the past is fully elapsed; the future
    # hasn't started. Never divide by the calendar twice.
    if (today.year, today.month) == (year, mon):
        elapsed = today.day / days_in_month  # unrounded — money math first
    elif (today.year, today.month) > (year, mon):
        elapsed = 1.0
    else:
        elapsed = 0.0
    elapsed_frac = round(elapsed, 4)  # the display copy
    discretionary_budget = round(max(income_planned - recurring_expense_planned, 0.0), 2)
    budget_to_date = round(discretionary_budget * elapsed, 2)
    pace = {
        "elapsed_frac": elapsed_frac,
        "discretionary_budget": discretionary_budget,
        "budget_to_date": budget_to_date,
        "actual_total": actual_total,
        # positive = headroom remains at this point of the month
        "headroom_to_date": round(budget_to_date - actual_total, 2),
        "over_pace": actual_total > budget_to_date,
    }

    notes = [
        "recurring flows are monthly (v1); weekly cadences need doubling by hand",
        "leftover subtracts BOTH recurring bills and logged spending — a bill "
        "logged as a spend is double-counted; categorize bill payments under "
        "the bill's category so the overlap is visible",
    ]
    if income_planned == 0 and not flows:
        notes.append("no recurring flows recorded — say 'my rent is 1500 a "
                     "month' or 'I make 5000 a month' to set the budget frame")

    return {
        "month": month,
        "days_in_month": days_in_month,
        "income_planned": income_planned,
        "recurring_expense_planned": recurring_expense_planned,
        "recurring_expense_by_category": {
            k: round(v, 2) for k, v in sorted(recurring_expense.items())},
        "actual_total": actual_total,
        "actual_by_category": {
            k: round(v, 2) for k, v in sorted(
                actual_by_category.items(), key=lambda kv: -kv[1])},
        "leftover": leftover,
        "pace": pace,
        "notes": notes,
    }


def card_utilization(cards: list[CardSpec]) -> dict:
    """Per-card utilization with the 30% caution line.

    Cards without a stated limit cannot have a utilization — they are named,
    never silently dropped and never guessed at.
    """
    rows = []
    unknown = []
    for c in cards:
        if c.credit_limit is None or c.credit_limit <= 0:
            unknown.append(c.name)
            continue
        frac = round(c.balance / c.credit_limit, 4)
        rows.append({
            "name": c.name,
            "balance": round(c.balance, 2),
            "credit_limit": round(c.credit_limit, 2),
            "utilization_frac": frac,
            "above_caution": frac > UTILIZATION_CAUTION_FRAC,
            "balance_asof": c.balance_asof,
        })
    rows.sort(key=lambda r: -r["utilization_frac"])
    total_balance = round(sum(r["balance"] for r in rows), 2)
    total_limit = round(sum(r["credit_limit"] for r in rows), 2)
    return {
        "cards": rows,
        "overall_utilization_frac": (
            round(total_balance / total_limit, 4) if total_limit else None),
        "caution_line_frac": UTILIZATION_CAUTION_FRAC,
        "any_above_caution": any(r["above_caution"] for r in rows),
        "no_limit_stated": unknown,
    }


def next_due_date(due_day: int, today: date) -> date:
    """The next calendar date a due_day (1..28) lands on, today included."""
    if not (1 <= due_day <= 28):
        raise BudgetError(f"due_day must be 1..28, got {due_day}")
    if due_day >= today.day:
        return date(today.year, today.month, due_day)
    year, mon = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
    return date(year, mon, due_day)


def bills_due_within(dues: list[DueSpec], today: date | None = None,
                     horizon_days: int = 7) -> list[dict]:
    """Debts whose next due date falls within the horizon, soonest first.

    Only owner-stated due days are used — statement dates are NOT stored
    (only due_day is); callers must name that gap rather than approximate.
    """
    today = today or date.today()
    out = []
    for d in dues:
        due = next_due_date(d.due_day, today)
        days_until = (due - today).days
        if days_until <= horizon_days:
            out.append({
                "name": d.name,
                "due_date": due.isoformat(),
                "days_until": days_until,
                "min_payment": round(d.min_payment, 2),
            })
    out.sort(key=lambda r: r["days_until"])
    return out


__all__ = [
    "UTILIZATION_CAUTION_FRAC", "BudgetError",
    "FlowSpec", "SpendSpec", "CardSpec", "DueSpec",
    "month_view", "card_utilization", "next_due_date", "bills_due_within",
]
