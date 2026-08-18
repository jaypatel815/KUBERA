"""T016c — the owner's REAL fills, landing daily (D026).

T016 ended with a twice-verified read-only Schwab sync; this is what turns
that verified pipe into a LIVING record: scripts/sync.py now pulls the last
`days` of transactions on every run, maps them through the reconciled mapper,
and upserts fills (with the broker's own commissions/fees) and cash movements
into the same tables the behavioural stack reads.

Dedup is the same discipline as the Alpaca sync (T036): per (account,
external_id) via the table's unique constraint, so overlapping windows and
re-runs are always safe. Unmapped rows are COUNTED AND RETURNED, never
dropped — the reconcile scripts remain the audit trail.

NEVER FATAL BY DESIGN (the ticket's own requirement): the refresh token
expires roughly weekly, and a lapsed token must degrade to a named note —
"run schwab_auth.py --write" — while the rest of the sync carries on. A
missing config skips quietly with a note. Real mapping problems still raise;
silence is only for the two EXPECTED conditions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from data.models import CashFlow, Transaction
from data.schwab import SchwabClient, map_transactions
from data.sync import ensure_account


@dataclass(frozen=True)
class SchwabSyncResult:
    fills_inserted: int
    fills_skipped: int
    cash_inserted: int
    cash_skipped: int
    unmapped: int
    account_masked: str

    def summary(self) -> str:
        return (f"schwab {self.account_masked}: fills +{self.fills_inserted}/"
                f"{self.fills_skipped} known, cash +{self.cash_inserted}/"
                f"{self.cash_skipped} known, {self.unmapped} unmapped")


def sync_schwab_fills(session: Session, client: SchwabClient,
                      days: int = 30) -> SchwabSyncResult:
    """Pull the trailing window of real transactions and upsert, deduped.

    30 days of overlap per run is deliberate: dedup makes it free, and it
    means a couple of missed days (machine off, token lapsed) heal on the
    next successful run without anyone noticing a gap.
    """
    if days < 1:
        raise ValueError("days must be >= 1")
    accounts = client.list_accounts()
    account = accounts[0]
    # The encrypted hash is Schwab's own stable, non-PII account address —
    # exactly what belongs in the DB instead of the account number.
    acct = ensure_account(session, account.hash_value, "USD")

    end = datetime.now(timezone.utc)
    rows = client.get_transactions(account.hash_value, end - timedelta(days=days), end)
    report = map_transactions(rows)

    known_fills = set(
        session.execute(
            select(Transaction.external_id).where(Transaction.account_id == acct.id)
        ).scalars().all()
    )
    f_ins = f_skip = 0
    for f in report.fills:
        if f.external_id in known_fills:
            f_skip += 1
            continue
        session.add(Transaction(
            account_id=acct.id,
            external_id=f.external_id,
            symbol=f.symbol,
            side=f.side,
            qty=f.qty,
            price=f.price,
            occurred_at=f.occurred_at,
            source=f.source,
            order_id=f.order_id or None,
            fill_type=f.fill_type,
            commission=f.commission,
            fees=f.fees,
        ))
        known_fills.add(f.external_id)
        f_ins += 1

    known_cash = set(
        session.execute(
            select(CashFlow.external_id).where(CashFlow.account_id == acct.id)
        ).scalars().all()
    )
    c_ins = c_skip = 0
    for c in report.cash:
        if c.external_id in known_cash:
            c_skip += 1
            continue
        session.add(CashFlow(
            account_id=acct.id,
            external_id=c.external_id,
            kind=c.kind,
            amount=c.amount,
            occurred_at=c.occurred_at,
            source=c.source,
        ))
        known_cash.add(c.external_id)
        c_ins += 1

    session.commit()
    return SchwabSyncResult(
        fills_inserted=f_ins, fills_skipped=f_skip,
        cash_inserted=c_ins, cash_skipped=c_skip,
        unmapped=len(report.unmapped),
        account_masked=account.number_masked,
    )
