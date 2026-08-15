"""Watchlist membership (T068) — add, remove, list. Ranking lives in
analysis/ranking.py; this module only manages the table."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from data.models import WatchlistEntry


def add_symbol(db: Session, symbol: str, note: str | None = None) -> WatchlistEntry:
    """Idempotent: re-adding updates the note instead of erroring."""
    sym = symbol.upper().strip()
    if not sym or len(sym) > 10:
        raise ValueError(f"bad symbol {symbol!r}")
    row = db.execute(
        select(WatchlistEntry).where(WatchlistEntry.symbol == sym)
    ).scalar_one_or_none()
    if row is None:
        row = WatchlistEntry(symbol=sym, note=note)
        db.add(row)
    elif note is not None:
        row.note = note
    db.commit()
    return row


def remove_symbol(db: Session, symbol: str) -> bool:
    row = db.execute(
        select(WatchlistEntry).where(WatchlistEntry.symbol == symbol.upper().strip())
    ).scalar_one_or_none()
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def list_symbols(db: Session) -> list[WatchlistEntry]:
    return list(db.execute(
        select(WatchlistEntry).order_by(WatchlistEntry.symbol)
    ).scalars())
