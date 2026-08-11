"""Snapshot sync (T014): fetch live account + positions, write timestamped rows.

Pure service logic — no scheduling in here. `scripts/sync.py` runs it one-shot or
in a loop; Windows Task Scheduler / cron can call the one-shot mode.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from data.alpaca import AlpacaClient
from data.models import AccountSnapshot as AccountSnapshotRow
from data.models import BrokerAccount
from data.models import PositionSnapshot as PositionSnapshotRow

log = logging.getLogger("kubera.sync")

BROKER = "alpaca-paper"


@dataclass(frozen=True)
class SyncResult:
    account_external_id: str
    equity: float
    positions: int
    asof: datetime


def ensure_account(session: Session, external_id: str, currency: str) -> BrokerAccount:
    """Idempotent: one row per (broker, external_id), created on first sight."""
    acct = session.execute(
        select(BrokerAccount).where(
            BrokerAccount.broker == BROKER, BrokerAccount.external_id == external_id
        )
    ).scalar_one_or_none()
    if acct is None:
        acct = BrokerAccount(broker=BROKER, external_id=external_id, currency=currency)
        session.add(acct)
        session.flush()  # assign id
    return acct


def sync_once(session: Session, client: AlpacaClient) -> SyncResult:
    """One full snapshot: account row upsert + account/position snapshot inserts."""
    live_acct = client.get_account()
    positions = client.get_positions()

    acct = ensure_account(session, live_acct.external_id, live_acct.currency)
    session.add(
        AccountSnapshotRow(
            account_id=acct.id,
            equity=live_acct.equity,
            cash=live_acct.cash,
            buying_power=live_acct.buying_power,
            asof=live_acct.asof,
            source=live_acct.source,
        )
    )
    for p in positions:
        session.add(
            PositionSnapshotRow(
                account_id=acct.id,
                symbol=p.symbol,
                qty=p.qty,
                avg_entry_price=p.avg_entry_price,
                current_price=p.current_price,
                market_value=p.market_value,
                cost_basis=p.cost_basis,
                unrealized_pl=p.unrealized_pl,
                asof=p.asof,
                source=p.source,
            )
        )
    session.commit()
    result = SyncResult(
        account_external_id=live_acct.external_id,
        equity=live_acct.equity,
        positions=len(positions),
        asof=live_acct.asof,
    )
    log.info(
        "sync ok: account=%s equity=%.2f positions=%d asof=%s",
        result.account_external_id, result.equity, result.positions, result.asof.isoformat(),
    )
    return result
