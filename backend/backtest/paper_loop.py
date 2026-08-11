"""Paper-trading loop (T032): strategy → risk gate → Alpaca PAPER order → audit log.

One cycle:
1. Fetch daily bars; the strategy turns them into a target weight [0..1].
2. target position value = weight × allocation_frac × account equity
   (allocation_frac is the slice of the account this strategy may manage; the risk
   engine's per-symbol cap applies on top and always wins).
3. Feed equity to the risk engine (day baseline + circuit breaker), then run the delta
   order through pre_trade_check(). REJECTED → logged, nothing sent. Approved → order
   placed on the paper account.
4. Every cycle writes a SignalLog row — ordered, rejected, or no_action — with the data
   snapshot it was based on. If it isn't in the log, it didn't happen.

Nothing in this module can reach live capital: AlpacaClient physically has no live code
path (§7.4 rail), and every order passes the fail-closed RiskEngine first.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backtest.engine import Strategy
from data.alpaca import AlpacaClient
from data.market_data import MarketDataClient
from data.models import SignalLog
from risk.engine import OrderRequest, RiskEngine
from risk.persistence import persist_risk_state, restore_risk_state

log = logging.getLogger("kubera.paper_loop")

MIN_TRADE_VALUE = 100.0  # ignore dust rebalances below this notional


@dataclass(frozen=True)
class CycleResult:
    action: str  # "ordered" | "rejected" | "no_action"
    symbol: str
    signal_weight: float
    target_value: float
    current_value: float
    detail: str
    order_external_id: str | None = None


def run_paper_cycle(
    db: Session,
    alpaca: AlpacaClient,
    market: MarketDataClient,
    risk: RiskEngine,
    strategy: Strategy,
    symbol: str,
    allocation_frac: float = 0.15,
    history_days: int = 400,
    min_trade_value: float = MIN_TRADE_VALUE,
) -> CycleResult:
    if not 0 < allocation_frac <= 1:
        raise ValueError(f"allocation_frac must be in (0, 1], got {allocation_frac}")
    symbol = symbol.upper()

    # 1. data snapshot
    bars = market.get_daily_bars(symbol, days=history_days)
    if len(bars.bars) < 2:
        raise ValueError(f"insufficient history for {symbol!r}")
    closes = [b.close for b in bars.bars]
    last_price = closes[-1]

    # 2. signal + account state
    weight = strategy(closes)
    acct = alpaca.get_account()
    positions = alpaca.get_positions()
    held = next((p for p in positions if p.symbol == symbol), None)
    current_value = held.market_value if held else 0.0
    target_value = weight * allocation_frac * acct.equity

    # 3. risk engine: restore persisted state (a restart must never forget a trip),
    #    then day management + breaker feed, then persist the updated state.
    restore_risk_state(db, risk)
    today = datetime.now(timezone.utc).date().isoformat()
    if risk.day != today:
        risk.start_day(acct.equity, today)
    risk.record_equity(acct.equity, acct.asof)
    persist_risk_state(db, risk)

    strategy_name = getattr(strategy, "__name__", "strategy")

    def log_row(action: str, reasons: str | None, order_id: str | None) -> None:
        db.add(SignalLog(
            strategy=strategy_name, symbol=symbol, signal_weight=weight,
            equity=acct.equity, current_value=current_value, target_value=target_value,
            action=action, reasons=reasons, order_external_id=order_id,
            bars_asof=bars.asof, source=bars.source,
        ))
        db.commit()

    # 4. delta -> order
    delta = target_value - current_value
    if abs(delta) < min_trade_value:
        log_row("no_action", f"delta {delta:.2f} below min trade {min_trade_value:.2f}", None)
        return CycleResult("no_action", symbol, weight, target_value, current_value,
                           f"within {min_trade_value:.0f} of target")

    side = "buy" if delta > 0 else "sell"
    qty = round(abs(delta) / last_price, 3)
    if side == "sell" and held is not None:
        qty = min(qty, held.qty)  # never sell more than held (long-only v1)
    if qty <= 0:
        log_row("no_action", "computed qty rounded to zero", None)
        return CycleResult("no_action", symbol, weight, target_value, current_value,
                           "qty rounded to zero")

    order = OrderRequest(symbol=symbol, side=side, qty=qty, est_price=last_price)
    decision = risk.pre_trade_check(order, acct.equity, current_value)
    if not decision.approved:
        reasons = "; ".join(decision.reasons)
        log_row("rejected", reasons, None)
        log.warning("cycle REJECTED %s %s: %s", side, symbol, reasons)
        return CycleResult("rejected", symbol, weight, target_value, current_value, reasons)

    placed = alpaca.place_order(symbol, side, qty)
    log_row("ordered", None, placed.external_id)
    detail = f"{side} {qty} {symbol} @ ~{last_price:.2f} (order {placed.status})"
    log.info("cycle ORDERED: %s", detail)
    return CycleResult("ordered", symbol, weight, target_value, current_value,
                       detail, placed.external_id)
