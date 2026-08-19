"""Risk engine v1 (T033) — the hard stop the LLM cannot reason around (spec §8).

Design principles, in order:
1. FAIL CLOSED. An uninitialized engine rejects every order. Unknown state = no trade.
2. The circuit breaker never resets itself. Not on a new day, not on recovery — only an
   explicit human-initiated reset() clears it (spec §8: "requiring manual reset").
3. A tripped breaker halts ALL orders, sells included. The owner can always act manually
   at the broker; KUBERA stops acting the moment the day goes badly wrong.
4. Every decision is timestamped and carries every violated rule, with the numbers.

This module is pure logic — no I/O, no broker calls. The paper-trading loop (T032) feeds
it equity marks and routes every order through pre_trade_check(). Persisting trip state
across process restarts is T032's responsibility (DB), noted here so nobody assumes it.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

log = logging.getLogger("kubera.risk")


class LockoutActiveError(RuntimeError):
    """Raised when a breaker reset is attempted during the cooling-off period.

    This is the commitment device (owner-requested, 2026-08-12): the person who set the
    limit must not be able to remove it in the same emotional moment it tripped."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class RiskLimits:
    """Hard limits. Defaults are deliberately conservative; owner tunes via config later."""

    max_position_frac: float = 0.20  # per-symbol cap as fraction of portfolio equity
    daily_loss_limit_frac: float = 0.03  # halt at -3% from the day's starting equity
    # Cooling-off period: after a trip, reset() is refused for this many hours.
    # Default ~20h pushes the reset past "one more trade" into the next session.
    cooldown_hours: float = 20.0
    # Vol-parity sizing (T078): max loss per trade if the ATR-based stop is hit, as a
    # fraction of equity. Band capped at 5% — beyond that isn't sizing, it's gambling.
    risk_per_trade_frac: float = 0.01
    stop_atr_multiple: float = 2.0

    def __post_init__(self):
        if not 0 < self.max_position_frac <= 1:
            raise ValueError(f"max_position_frac must be in (0, 1], got {self.max_position_frac}")
        if not 0 < self.daily_loss_limit_frac < 1:
            raise ValueError(
                f"daily_loss_limit_frac must be in (0, 1), got {self.daily_loss_limit_frac}"
            )
        if not 0 <= self.cooldown_hours <= 24 * 7:
            raise ValueError(f"cooldown_hours must be in [0, 168], got {self.cooldown_hours}")
        if not 0 < self.risk_per_trade_frac <= 0.05:
            raise ValueError(
                f"risk_per_trade_frac must be in (0, 0.05], got {self.risk_per_trade_frac}"
            )
        if not 0 < self.stop_atr_multiple <= 10:
            raise ValueError(
                f"stop_atr_multiple must be in (0, 10], got {self.stop_atr_multiple}"
            )


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: str  # "buy" | "sell"
    qty: float
    est_price: float

    @property
    def notional(self) -> float:
        return self.qty * self.est_price


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    reasons: list[str]  # empty iff approved; every violated rule, with numbers
    checked_at: datetime


@dataclass
class RiskEngine:
    limits: RiskLimits = field(default_factory=RiskLimits)
    _day_start_equity: float | None = None
    _day: str | None = None
    _tripped: bool = False
    _trip_reason: str | None = None
    _lockout_until: datetime | None = None
    # T065: owner-disabled symbols — BUYS refused, sells always allowed
    # (reducing risk is never blocked). Persisted with the rest of the state.
    _disabled_symbols: frozenset[str] = frozenset()

    # -- state ---------------------------------------------------------------

    @property
    def tripped(self) -> bool:
        return self._tripped

    @property
    def trip_reason(self) -> str | None:
        return self._trip_reason

    @property
    def lockout_until(self) -> datetime | None:
        return self._lockout_until

    @property
    def day(self) -> str | None:
        return self._day

    @property
    def day_start_equity(self) -> float | None:
        return self._day_start_equity

    @property
    def disabled_symbols(self) -> frozenset[str]:
        return self._disabled_symbols

    def set_disabled_symbols(self, symbols) -> None:
        """T065: replace the disabled set (upper-cased). The CLI and
        persistence layer are the only intended callers — chat cannot reach
        this (no tool exposes it; changing a rail stays a deliberate act)."""
        self._disabled_symbols = frozenset(str(s).upper() for s in symbols if s)

    def restore(
        self,
        day: str | None,
        day_start_equity: float | None,
        tripped: bool,
        trip_reason: str | None,
        lockout_until: datetime | None = None,
    ) -> None:
        """Persistence-layer use ONLY (risk/persistence.py): rehydrate saved state so a
        process restart cannot forget a tripped breaker OR its lockout."""
        self._day = day
        self._day_start_equity = day_start_equity
        self._tripped = tripped
        self._trip_reason = trip_reason
        self._lockout_until = lockout_until
        if tripped:
            log.warning("risk state restored TRIPPED: %s", trip_reason)

    def start_day(self, equity: float, day: str) -> None:
        """Set the day's baseline. Does NOT clear a tripped breaker (principle 2)."""
        if equity <= 0:
            raise ValueError(f"day-start equity must be > 0, got {equity}")
        self._day_start_equity = equity
        self._day = day
        log.info("risk day start: day=%s equity=%.2f tripped=%s", day, equity, self._tripped)

    def record_equity(self, equity: float, asof: datetime) -> None:
        """Feed an equity mark; trips the breaker past the daily loss limit. Idempotent."""
        if self._day_start_equity is None:
            raise ValueError("record_equity before start_day — initialize the day first")
        if self._tripped:
            return
        loss_frac = (self._day_start_equity - equity) / self._day_start_equity
        if loss_frac >= self.limits.daily_loss_limit_frac:
            self._tripped = True
            self._lockout_until = asof + timedelta(hours=self.limits.cooldown_hours)
            self._trip_reason = (
                f"daily loss circuit breaker: equity {equity:.2f} is "
                f"{loss_frac:.2%} below day-start {self._day_start_equity:.2f} "
                f"(limit {self.limits.daily_loss_limit_frac:.2%}) at {asof.isoformat()}"
            )
            log.warning(
                "CIRCUIT BREAKER TRIPPED: %s (reset locked until %s)",
                self._trip_reason, self._lockout_until.isoformat(),
            )

    def reset(self, note: str, now: datetime | None = None) -> None:
        """Manual, human-initiated reset — the ONLY way a trip clears, and NOT during
        the cooling-off period. The commitment device has no override parameter,
        deliberately: the person who set the limit must not be able to remove it in
        the moment it starts hurting (owner request, 2026-08-12)."""
        now = now or _utcnow()
        if self._tripped and self._lockout_until and now < self._lockout_until:
            remaining = self._lockout_until - now
            hours = remaining.total_seconds() / 3600
            raise LockoutActiveError(
                f"cooling-off period active: reset available at "
                f"{self._lockout_until.isoformat()} ({hours:.1f}h from now). "
                "This lockout is the point — step away from the screen."
            )
        log.warning("circuit breaker reset: %s (was: %s)", note, self._trip_reason)
        self._tripped = False
        self._trip_reason = None
        self._lockout_until = None

    # -- the gate ------------------------------------------------------------

    def pre_trade_check(
        self,
        order: OrderRequest,
        portfolio_equity: float,
        current_position_value: float,
    ) -> RiskDecision:
        """Every order passes through here BEFORE reaching any broker. Fail closed."""
        reasons: list[str] = []

        if self._day_start_equity is None:
            reasons.append("risk engine not initialized: start_day() has not been called")
        if self._tripped:
            reasons.append(f"trading halted — {self._trip_reason}; manual reset required")
        if order.side not in ("buy", "sell"):
            reasons.append(f"unknown order side '{order.side}'")
        if order.qty <= 0:
            reasons.append(f"qty must be > 0, got {order.qty}")
        if order.est_price <= 0:
            reasons.append(f"est_price must be > 0, got {order.est_price}")
        if portfolio_equity <= 0:
            reasons.append(f"portfolio equity must be > 0, got {portfolio_equity}")

        if not reasons and order.side == "buy" and \
                order.symbol.upper() in self._disabled_symbols:
            reasons.append(
                f"{order.symbol.upper()} is DISABLED for new buys "
                "(scripts/risk_symbols.py --enable to lift; sells were never "
                "blocked — reducing risk is always allowed)")

        if not reasons and order.side == "buy":
            projected = current_position_value + order.notional
            cap = self.limits.max_position_frac * portfolio_equity
            if projected > cap:
                reasons.append(
                    f"position cap: projected {order.symbol} exposure {projected:.2f} "
                    f"exceeds {self.limits.max_position_frac:.0%} of equity "
                    f"{portfolio_equity:.2f} (cap {cap:.2f})"
                )

        decision = RiskDecision(approved=not reasons, reasons=reasons, checked_at=_utcnow())
        log.info(
            "pre-trade check: %s %s %.4f @ %.2f -> %s%s",
            order.side, order.symbol, order.qty, order.est_price,
            "APPROVED" if decision.approved else "REJECTED",
            "" if decision.approved else f" ({'; '.join(reasons)})",
        )
        return decision
