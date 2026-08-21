"""T152 (D039 Phase 9) — the household store: debts, recurring flows, spending.

Thin and STRICT. Units are refused, not guessed: apr_frac is a FRACTION
(0.249 for 24.9% APR) and anything that smells like a percent (> 1.5) is
rejected with the conversion spelled out — the chat layer (T155) translates
the owner's words; the store never does unit arithmetic on his behalf.
Manual balances carry balance_asof (the date he told us) so downstream can
say "as you told me on <date>" and flag statement-cycle staleness. Analysis
(payoff schedules, budgets, utilization) lives in analysis/ — this module
only keeps the facts.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from data.models import Debt, RecurringFlow, SpendingEntry

DEBT_KINDS = ("credit_card", "loan", "other")
FLOW_DIRECTIONS = ("income", "expense")
STALE_BALANCE_DAYS = 35  # one statement cycle + slack — then "as told" goes stale


class HouseholdError(ValueError):
    """Named refusal — bad units or impossible values never reach the DB."""


def _check_debt(name: str, kind: str, balance: float, apr_frac: float,
                min_payment: float, credit_limit: float | None,
                due_day: int | None) -> None:
    if not name.strip():
        raise HouseholdError("debt needs a name")
    if kind not in DEBT_KINDS:
        raise HouseholdError(f"kind must be one of {DEBT_KINDS}, got {kind!r}")
    if balance < 0:
        raise HouseholdError(f"balance cannot be negative ({balance})")
    if apr_frac < 0:
        raise HouseholdError(f"apr_frac cannot be negative ({apr_frac})")
    if apr_frac > 1.5:
        raise HouseholdError(
            f"apr_frac is a FRACTION — {apr_frac} looks like a percent; "
            f"24.9% APR is apr_frac=0.249 (you sent {apr_frac})")
    if min_payment < 0:
        raise HouseholdError(f"min_payment cannot be negative ({min_payment})")
    if credit_limit is not None and credit_limit <= 0:
        raise HouseholdError(f"credit_limit must be positive ({credit_limit})")
    if due_day is not None and not (1 <= due_day <= 28):
        raise HouseholdError(
            f"due_day must be 1..28 ({due_day}) — 29+ does not exist in "
            "February and a due date that skips months is a missed payment")


def upsert_debt(session: Session, *, name: str, kind: str, balance: float,
                apr_frac: float, min_payment: float,
                credit_limit: float | None = None, due_day: int | None = None,
                balance_asof: str | None = None) -> Debt:
    """Insert or update by name. Every update restamps balance_asof — a
    re-statement of the balance is a new observation."""
    _check_debt(name, kind, balance, apr_frac, min_payment, credit_limit, due_day)
    asof = balance_asof or date.today().isoformat()
    date.fromisoformat(asof)  # refuse non-ISO input loudly
    row = session.execute(
        select(Debt).where(Debt.name == name)).scalars().first()
    if row is None:
        row = Debt(name=name, kind=kind, balance=balance, apr_frac=apr_frac,
                   min_payment=min_payment, credit_limit=credit_limit,
                   due_day=due_day, balance_asof=asof)
        session.add(row)
    else:
        row.kind, row.balance, row.apr_frac = kind, balance, apr_frac
        row.min_payment, row.credit_limit = min_payment, credit_limit
        row.due_day, row.balance_asof = due_day, asof
    session.commit()
    return row


def list_debts(session: Session) -> list[Debt]:
    return list(session.execute(
        select(Debt).order_by(Debt.apr_frac.desc())).scalars().all())


def remove_debt(session: Session, name: str) -> bool:
    row = session.execute(
        select(Debt).where(Debt.name == name)).scalars().first()
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True


def balance_is_stale(debt: Debt, today: date | None = None) -> bool:
    """Manual-data recency (D039): one statement cycle after the owner
    stated a balance, it stops being presentable as current."""
    today = today or date.today()
    return (today - date.fromisoformat(debt.balance_asof)).days > STALE_BALANCE_DAYS


def upsert_flow(session: Session, *, name: str, direction: str, amount: float,
                category: str = "uncategorized") -> RecurringFlow:
    if not name.strip():
        raise HouseholdError("flow needs a name")
    if direction not in FLOW_DIRECTIONS:
        raise HouseholdError(
            f"direction must be one of {FLOW_DIRECTIONS}, got {direction!r}")
    if amount <= 0:
        raise HouseholdError(
            f"amount must be positive ({amount}) — direction carries the sign")
    row = session.execute(
        select(RecurringFlow).where(RecurringFlow.name == name)
    ).scalars().first()
    if row is None:
        row = RecurringFlow(name=name, direction=direction, amount=amount,
                            category=category)
        session.add(row)
    else:
        row.direction, row.amount, row.category = direction, amount, category
    session.commit()
    return row


def list_flows(session: Session) -> list[RecurringFlow]:
    return list(session.execute(
        select(RecurringFlow).order_by(RecurringFlow.direction,
                                       RecurringFlow.amount.desc())
    ).scalars().all())


def log_spending(session: Session, *, amount: float, category: str,
                 on: str | None = None, note: str | None = None,
                 source: str = "manual",
                 import_key: str | None = None) -> SpendingEntry | None:
    """One spend. With an import_key (CSV, T156) the write is idempotent:
    a duplicate key returns None and changes nothing."""
    if amount <= 0:
        raise HouseholdError(f"amount must be positive ({amount})")
    day = on or date.today().isoformat()
    date.fromisoformat(day)
    if import_key is not None:
        dup = session.execute(
            select(SpendingEntry).where(SpendingEntry.import_key == import_key)
        ).scalars().first()
        if dup is not None:
            return None
    row = SpendingEntry(date=day, amount=amount,
                        category=(category or "uncategorized").strip().lower(),
                        note=note, source=source, import_key=import_key)
    session.add(row)
    session.commit()
    return row


def spending_between(session: Session, start: str, end: str) -> list[SpendingEntry]:
    return list(session.execute(
        select(SpendingEntry)
        .where(SpendingEntry.date >= start, SpendingEntry.date <= end)
        .order_by(SpendingEntry.date)
    ).scalars().all())
