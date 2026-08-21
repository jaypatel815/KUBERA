"""T155 — one household composition, shared by GET /api/household and the
get_household chat tool (the monitor_service pattern: the dashboard and the
voice must never disagree about the same numbers).

Raises sqlalchemy OperationalError when the tables are missing — the caller
maps it to its own named refusal (503 for HTTP, ToolError for chat).
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from analysis.budget import (
    CardSpec,
    DueSpec,
    FlowSpec,
    SpendSpec,
    bills_due_within,
    card_utilization,
    month_view,
)
from analysis.payoff import DebtSpec, PayoffImpossible, compare_strategies
from data.household import balance_is_stale, list_debts, list_flows, spending_between

ALEMBIC_HINT = ("household tables not initialized — run: alembic -c "
                "backend/alembic.ini upgrade head")


def compose_household(session: Session) -> dict:
    """Debts + payoff + budget + utilization + bills, every number from
    tested engines, every manual figure carrying the date it was stated."""
    debts = list_debts(session)
    flows = list_flows(session)
    month = date.today().strftime("%Y-%m")
    spends = spending_between(session, f"{month}-01", f"{month}-31")

    rows = [{
        "name": d.name, "kind": d.kind, "balance": d.balance,
        "apr_frac": d.apr_frac, "min_payment": d.min_payment,
        "credit_limit": d.credit_limit,
        "utilization_frac": (round(d.balance / d.credit_limit, 4)
                             if d.credit_limit else None),
        "balance_asof": d.balance_asof,
        "stale": balance_is_stale(d),
    } for d in debts]

    payoff: dict = {"available": False, "why": "no debts recorded"}
    if rows:
        specs = [DebtSpec(d.name, d.balance, d.apr_frac, d.min_payment)
                 for d in debts]
        try:
            c = compare_strategies(specs)
            payoff = {
                "available": True,
                "avalanche": asdict(c["avalanche"]),
                "snowball": asdict(c["snowball"]),
                "interest_saved_by_avalanche": c["interest_saved_by_avalanche"],
                "months_difference": c["months_difference"],
                "note": c["note"],
            }
        except PayoffImpossible as e:
            payoff = {"available": False, "why": str(e)}

    # T154 — the budget engine owns every derived number below
    budget = month_view(
        [FlowSpec(f.name, f.direction, f.amount, f.category) for f in flows],
        [SpendSpec(s.date, s.amount, s.category) for s in spends],
        month)
    utilization = card_utilization([
        CardSpec(d.name, d.balance, d.credit_limit, d.balance_asof)
        for d in debts if d.kind == "credit_card"])
    caution_by_name = {c["name"]: c["above_caution"]
                       for c in utilization["cards"]}
    for r in rows:
        r["above_caution"] = caution_by_name.get(r["name"], False)
    bills = bills_due_within([
        DueSpec(d.name, d.due_day, d.min_payment)
        for d in debts if d.due_day is not None])

    return {
        "debts": rows,
        "total_balance": round(sum(d.balance for d in debts), 2),
        "any_stale": any(r["stale"] for r in rows),
        "payoff": payoff,
        "budget": budget,
        "utilization": utilization,
        "bills_due_7d": bills,
        "asof": datetime.now(timezone.utc).isoformat(),
        "note": ("owner-stated balances; arithmetic, not tax or credit "
                 "advice; stale = older than one statement cycle; statement "
                 "dates are not tracked — only due days are"),
    }
