"""Database schema v1 (T013) — SQLAlchemy 2.0 declarative models.

Money fields are floats for consistency with the analysis layer; the determinism rule
(AGENTS.md) is about WHO computes — tested code, never the LLM — not float vs Decimal.
Timestamps are stored via UTCDateTime, which refuses naive datetimes on write and
guarantees tz-aware UTC on read, on SQLite today and Postgres later (D007).
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
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


class Conversation(Base):
    """One chat thread with KUBERA."""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    title: Mapped[str | None] = mapped_column(String(120), default=None)


class ChatMessage(Base):
    """Every message — user, assistant, and tool results — timestamped (spec §2.7):
    the full audit trail of what KUBERA said and exactly which data it said it from."""

    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_conversation_created", "conversation_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant" | "tool"
    content: Mapped[str | None] = mapped_column(String(8000), default=None)
    tool_calls_json: Mapped[str | None] = mapped_column(String(4000), default=None)
    tool_call_id: Mapped[str | None] = mapped_column(String(64), default=None)
    tool_name: Mapped[str | None] = mapped_column(String(64), default=None)
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class BacktestRun(Base):
    """Every backtest, recorded forever — the §7.4 promotion checklist's evidence base."""

    __tablename__ = "backtest_runs"
    __table_args__ = (Index("ix_backtest_strategy_ts", "strategy", "ts"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    strategy: Mapped[str] = mapped_column(String(48))
    params_json: Mapped[str] = mapped_column(String(512), default="{}")
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    start_date: Mapped[str] = mapped_column(String(10))
    end_date: Mapped[str] = mapped_column(String(10))
    bars_count: Mapped[int] = mapped_column()
    cost_bps: Mapped[float] = mapped_column(Float)
    cumulative_return: Mapped[float] = mapped_column(Float)
    volatility_ann: Mapped[float | None] = mapped_column(Float, default=None)
    sharpe_ann: Mapped[float | None] = mapped_column(Float, default=None)
    max_drawdown_frac: Mapped[float] = mapped_column(Float)
    n_rebalances: Mapped[int] = mapped_column()
    total_cost_frac: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(32))
    # T064 promotion gate: "pending" | "passed_walk_forward" | "failed_walk_forward"
    promotion_status: Mapped[str] = mapped_column(String(24), default="pending",
                                                 server_default="pending")
    # T092 parameter stability: JSON StabilityReport recorded beside the promotion —
    # a strategy that only works at one magic parameter is curve-fit, not edge.
    stability_json: Mapped[str | None] = mapped_column(String(2048), default=None)


class InvestmentPolicy(Base):
    """The owner's living Investment Policy Statement (T061, D014) — single row (id=1).
    Injected into every chat; recommendations are checked against it. Updates go through
    the confirmation-gated `update_ips` tool, so changing your own rules is deliberate."""

    __tablename__ = "investment_policy"

    id: Mapped[int] = mapped_column(primary_key=True)  # always 1
    objectives: Mapped[str | None] = mapped_column(String(500), default=None)
    target_annual_return_frac: Mapped[float | None] = mapped_column(Float, default=None)
    max_drawdown_frac: Mapped[float | None] = mapped_column(Float, default=None)
    horizon_years: Mapped[float | None] = mapped_column(Float, default=None)
    risk_tolerance: Mapped[str | None] = mapped_column(String(32), default=None)
    restrictions_json: Mapped[str] = mapped_column(String(2000), default="[]")
    prohibited_strategies_json: Mapped[str] = mapped_column(String(2000), default="[]")
    notes: Mapped[str | None] = mapped_column(String(1000), default=None)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class RiskState(Base):
    """Single-row persistence of the RiskEngine (id is always 1). Exists so a tripped
    circuit breaker SURVIVES process restarts — a restart must never bypass it (spec §8)."""

    __tablename__ = "risk_state"

    id: Mapped[int] = mapped_column(primary_key=True)  # always RISK_STATE_ID = 1
    day: Mapped[str | None] = mapped_column(String(10), default=None)
    day_start_equity: Mapped[float | None] = mapped_column(Float, default=None)
    tripped: Mapped[bool] = mapped_column(Boolean, default=False)
    trip_reason: Mapped[str | None] = mapped_column(String(512), default=None)
    lockout_until: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


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
    # T091 attribution tags, captured AT decision time (nullable: older rows/sells)
    regime_label: Mapped[str | None] = mapped_column(String(24), default=None)
    sub_strategy: Mapped[str | None] = mapped_column(String(48), default=None)
    entry_bucket: Mapped[str | None] = mapped_column(String(16), default=None)


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
    # T091: the broker ORDER id — the join key from a fill back to the logged
    # decision (signal_log.order_external_id) that placed it
    order_id: Mapped[str | None] = mapped_column(String(64), default=None, index=True)


class DecisionJournal(Base):
    """Every recommendation KUBERA makes, captured AT decision time (T063, D016/D018):
    the verdict with its regime context, entry/target/stop, and — critically — whether
    the owner FOLLOWED or OVERRODE it. Six months from now, "why did I buy that?" and
    "how calibrated is KUBERA?" are answered from this table, not from memory."""

    __tablename__ = "decision_journal"
    __table_args__ = (Index("ix_journal_symbol_ts", "symbol", "ts"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    symbol: Mapped[str] = mapped_column(String(16))
    verdict: Mapped[str] = mapped_column(String(16))  # buy|add|hold|trim|sell|avoid
    confidence: Mapped[float] = mapped_column(Float)  # stated 0..1, capped by persona
    thesis: Mapped[str] = mapped_column(String(1000))
    horizon_days: Mapped[int | None] = mapped_column(Integer, default=None)
    entry_price: Mapped[float | None] = mapped_column(Float, default=None)
    target_price: Mapped[float | None] = mapped_column(Float, default=None)
    stop_price: Mapped[float | None] = mapped_column(Float, default=None)
    key_risk: Mapped[str | None] = mapped_column(String(500), default=None)
    regime: Mapped[str | None] = mapped_column(String(24), default=None)
    regime_confidence: Mapped[float | None] = mapped_column(Float, default=None)
    followed: Mapped[bool | None] = mapped_column(Boolean, default=None)  # None=unmarked
    follow_note: Mapped[str | None] = mapped_column(String(500), default=None)
    conversation_id: Mapped[int | None] = mapped_column(Integer, default=None)
    source: Mapped[str] = mapped_column(String(24), default="chat")
