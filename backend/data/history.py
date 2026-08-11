"""Equity history from stored snapshots (T021).

Daily portfolio equity = for each calendar day, the LAST snapshot per account, summed
across accounts. One number per day, oldest first, as (ISO date, equity) points.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from data.models import AccountSnapshot


def equity_history(session: Session, days: int = 365) -> list[tuple[str, float]]:
    """(date, total_equity) per day from account snapshots, oldest first."""
    if not 1 <= days <= 3650:
        raise ValueError(f"days must be 1..3650, got {days}")
    rows = session.execute(
        select(AccountSnapshot.account_id, AccountSnapshot.equity, AccountSnapshot.asof)
        .order_by(AccountSnapshot.asof)
    ).all()
    # last snapshot per (day, account), then sum per day — in Python: snapshot counts
    # are small (a few per day), and this keeps the logic identical on SQLite/Postgres.
    last_per_day_account: dict[tuple[str, int], float] = {}
    for account_id, equity, asof in rows:
        last_per_day_account[(asof.date().isoformat(), account_id)] = equity
    totals: dict[str, float] = {}
    for (day, _account), equity in last_per_day_account.items():
        totals[day] = totals.get(day, 0.0) + equity
    points = sorted(totals.items())[-days:]
    return [(d, v) for d, v in points]
