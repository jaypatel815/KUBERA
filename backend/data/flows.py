"""Cash-flow sync (T060) — deposits and withdrawals into `cash_flows`, deduped.

Same discipline as fills: dedup per (account, external_id) via the unique
constraint, so re-running is always safe. These rows are what let TWR strip
"money moved" out of "the strategy worked".
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from data.alpaca import AlpacaClient
from data.models import CashFlow
from data.sync import ensure_account


@dataclass(frozen=True)
class FlowSyncResult:
    inserted: int
    skipped: int


def sync_cash_flows(session: Session, client: AlpacaClient) -> FlowSyncResult:
    live_acct = client.get_account()
    acct = ensure_account(session, live_acct.external_id, live_acct.currency)
    activities = client.get_cash_activities()

    known = set(
        session.execute(
            select(CashFlow.external_id).where(CashFlow.account_id == acct.id)
        ).scalars().all()
    )
    inserted = skipped = 0
    for a in activities:
        if a.external_id in known:
            skipped += 1
            continue
        session.add(CashFlow(
            account_id=acct.id,
            external_id=a.external_id,
            kind=a.kind,
            amount=a.amount,
            occurred_at=a.occurred_at,
            source=a.source,
        ))
        known.add(a.external_id)
        inserted += 1
    session.commit()
    return FlowSyncResult(inserted=inserted, skipped=skipped)


def flow_history(session: Session, days: int = 365) -> list[tuple[str, float]]:
    """[(YYYY-MM-DD, signed amount)] oldest first — the input TWR expects."""
    rows = session.execute(
        select(CashFlow).order_by(CashFlow.occurred_at)
    ).scalars().all()
    return [(r.occurred_at.date().isoformat(), r.amount) for r in rows]
