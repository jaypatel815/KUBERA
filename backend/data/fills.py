"""Fills sync (T036) — executed fills from the broker into `transactions`, deduped.

The ground truth layer: slippage (T088), live MAE/MFE (T089), attribution (T091),
and TWR (T060) all build on real fills. Dedup is per (account, external_id) via
the table's unique constraint — re-running is always safe.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from data.alpaca import AlpacaClient
from data.models import Transaction
from data.sync import ensure_account


@dataclass(frozen=True)
class FillSyncResult:
    inserted: int
    skipped: int  # already present (dedup)


def sync_fills(session: Session, client: AlpacaClient) -> FillSyncResult:
    """Fetch all available fills and insert the ones we have not seen."""
    live_acct = client.get_account()
    acct = ensure_account(session, live_acct.external_id, live_acct.currency)
    fills = client.get_fills()

    known = set(
        session.execute(
            select(Transaction.external_id).where(Transaction.account_id == acct.id)
        ).scalars().all()
    )
    inserted = skipped = 0
    for f in fills:
        if f.external_id in known:
            skipped += 1
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
        ))
        known.add(f.external_id)
        inserted += 1
    session.commit()
    return FillSyncResult(inserted=inserted, skipped=skipped)
