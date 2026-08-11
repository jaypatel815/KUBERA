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
from datetime import datetime, timezone

log = logging.getLogger("kubera.risk")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class RiskLimits:
    """Hard limits. Defaults are deliberately conservative; owner tunes via config later."""

    max_position_frac: float = 0.20  # per-symbol cap as fraction of portfolio equity
    daily_loss_limit_frac: float = 0.03  # halt at -3% from the day's starting equity

    def __post_init__(self):
        if not 0 < self.max_position_frac <= 1:
            raise ValueError(f"max_position_frac must be in (0, 1], got {self.max_position_frac}")
        if not 0 < self.daily_loss_limit_frac < 1:
            raise ValueError(
                f"daily_loss_limit_frac must be in (0, 1), got {self.daily_loss_limit_frac}"
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

    # -- state ---------------------------------------------------------------

    @property
    def tripped(self) -> bool:
        return self._tripped

    @property
    def trip_reason(self) -> str | None:
        return self._trip_reason

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
            self._trip_reason = (
                f"daily loss circuit breaker: equity {equity:.2f} is "
                f"{loss_frac:.2%} below day-start {self._day_start_equity:.2f} "
                f"(limit {self.limits.daily_loss_limit_frac:.2%}) at {asof.isoformat()}"
            )
            log.warning("CIRCUIT BREAKER TRIPPED: %s", self._trip_reason)

    def reset(self, note: str) -> None:
        """Manual, human-initiated reset — the ONLY way a trip clears."""
        log.warning("circuit breaker reset: %s (was: %s)", note, self._trip_reason)
        self._tripped = False
        self._trip_reason = None

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
