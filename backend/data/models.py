"""Database schema v1 (T013) — SQLAlchemy 2.0 declarative models.

Money fields are floats for consistency with the analysis layer; the determinism rule
(AGENTS.md) is about WHO computes — tested code, never the LLM — not float vs Decimal.
Timestamps are stored via UTCDateTime, which refuses naive datetimes on write and
guarantees tz-aware UTC on read, on SQLite today and Postgres later (D007).
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """DateTime that enforces tz-awareness in, and restores UTC tzinfo out (SQLite drops it)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime rejected — KUBERA timestamps are always tz-aware")
        return value.astimezone(timezone.utc)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class BrokerAccount(Base):
    """One connected brokerage account (e.g. the Alpaca paper account; Schwab later, D009)."""

    __tablename__ = "broker_accounts"
    __table_args__ = (UniqueConstraint("broker", "external_id", name="uq_broker_external"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    broker: Mapped[str] = mapped_column(String(32))  # "alpaca-paper", "schwab", ...
    external_id: Mapped[str] = mapped_column(String(64))
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class AccountSnapshot(Base):
    """Point-in-time account state, as fetched (asof) from the broker."""

    __tablename__ = "account_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("broker_accounts.id"))
    equity: Mapped[float] = mapped_column(Float)
    cash: Mapped[float] = mapped_column(Float)
    buying_power: Mapped[float] = mapped_column(Float)
    asof: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    source: Mapped[str] = mapped_column(String(32))


class PositionSnapshot(Base):
    """Point-in-time holding state. Current portfolio = latest snapshot per symbol."""

    __tablename__ = "position_snapshots"
    __table_args__ = (Index("ix_position_account_symbol_asof", "account_id", "symbol", "asof"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("broker_accounts.id"))
    symbol: Mapped[str] = mapped_column(String(16))
    qty: Mapped[float] = mapped_column(Float)
    avg_entry_price: Mapped[float] = mapped_column(Float)
    current_price: Mapped[float] = mapped_column(Float)
    market_value: Mapped[float] = mapped_column(Float)
    cost_basis: Mapped[float] = mapped_column(Float)
    unrealized_pl: Mapped[float] = mapped_column(Float)
    asof: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    source: Mapped[str] = mapped_column(String(32))


class SignalLog(Base):
    """Full audit trail of the paper loop (spec §2.7): every signal, every decision —
    ordered, rejected, or no_action — with the data snapshot it was based on."""

    __tablename__ = "signal_log"
    __table_args__ = (Index("ix_signal_symbol_ts", "symbol", "ts"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    strategy: Mapped[str] = mapped_column(String(48))
    symbol: Mapped[str] = mapped_column(String(16))
    signal_weight: Mapped[float] = mapped_column(Float)
    equity: Mapped[float] = mapped_column(Float)
    current_value: Mapped[float] = mapped_column(Float)
    target_value: Mapped[float] = mapped_column(Float)
    action: Mapped[str] = mapped_column(String(16))  # "ordered" | "rejected" | "no_action"
    reasons: Mapped[str | None] = mapped_column(String(1024), default=None)
    order_external_id: Mapped[str | None] = mapped_column(String(64), default=None)
    bars_asof: Mapped[datetime] = mapped_column(UTCDateTime)
    source: Mapped[str] = mapped_column(String(32))


class Transaction(Base):
    """Executed fills, deduped per account by the broker's own id."""

    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("account_id", "external_id", name="uq_txn_account_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("broker_accounts.id"))
    external_id: Mapped[str] = mapped_column(String(64))
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    side: Mapped[str] = mapped_column(String(8))  # "buy" | "sell"
    qty: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    source: Mapped[str] = mapped_column(String(32))
