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

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from analysis.metrics import atr
from analysis.regime import classify_regime
from backtest.engine import Strategy
from data.alpaca import AlpacaClient
from data.market_data import MarketDataClient
from data.models import SignalLog
from risk.engine import OrderRequest, RiskEngine
from risk.persistence import persist_risk_state, restore_risk_state
from risk.sizing import volatility_parity_notional
from risk.tiers import current_tier

log = logging.getLogger("kubera.paper_loop")

MIN_TRADE_VALUE = 100.0  # ignore dust rebalances below this notional
ATR_WINDOW = 14  # bars for the vol-parity sizer (T078); buys need ATR_WINDOW+1 bars


@dataclass(frozen=True)
class CycleResult:
    action: str  # "ordered" | "rejected" | "no_action" | "no_trade" (T055)
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
    # T055 — the no-trade condition (buys only; reducing risk is never blocked):
    max_trades_per_day: int = 5,   # overtrading guard across ALL symbols/strategies
    min_atr_frac: float = 0.001,   # expected-move proxy: ATR/price below this can't clear costs
    rvol_floor: float = 0.3,       # quiet-market check (with a bottom-quartile range width)
) -> CycleResult:
    if not 0 < allocation_frac <= 1:
        raise ValueError(f"allocation_frac must be in (0, 1], got {allocation_frac}")
    if max_trades_per_day < 1 or min_atr_frac < 0 or rvol_floor < 0:
        raise ValueError("max_trades_per_day >= 1; min_atr_frac and rvol_floor >= 0")
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

    # 4. delta -> vol-parity sizing (buys only; T078) -> order
    delta = target_value - current_value
    sizing_note = None
    if delta > 0:
        # Fail closed: a buy without enough history to size honestly is no trade.
        if len(bars.bars) < ATR_WINDOW + 1:
            reason = (f"insufficient history for ATR({ATR_WINDOW}) sizing: "
                      f"{len(bars.bars)} bars < {ATR_WINDOW + 1}")
            log_row("no_action", reason, None)
            return CycleResult("no_action", symbol, weight, target_value,
                               current_value, reason)
        highs = [b.high for b in bars.bars]
        lows = [b.low for b in bars.bars]
        atr_value = atr(highs, lows, closes, window=ATR_WINDOW)

        # T067: graduated risk tiers — friction BEFORE the breaker. Only while the
        # breaker is untripped (a tripped breaker must reject loudly at the gate).
        tier = None
        tier_note = None
        eff_min_atr_frac, eff_rvol_floor = min_atr_frac, rvol_floor
        size_multiplier = 1.0
        if not risk.tripped and risk.day_start_equity is not None:
            tier = current_tier(
                risk.day_start_equity, acct.equity, risk.limits.daily_loss_limit_frac
            )
            if tier.level >= 1:
                tier_note = (
                    f"risk tier {tier.level} ({tier.name}): "
                    f"{tier.budget_consumed_frac:.0%} of the daily loss budget "
                    f"consumed — {tier.effect}"
                )
            if tier.level >= 1:
                eff_min_atr_frac, eff_rvol_floor = min_atr_frac * 2, rvol_floor * 2
            if tier.level >= 2:
                size_multiplier = 0.5
            if tier.level >= 3:
                reason = f"no trade today: {tier_note} — capital preserved by design"
                log_row("no_trade", reason, None)
                log.warning("cycle NO_TRADE %s: %s", symbol, reason)
                return CycleResult("no_trade", symbol, weight, target_value,
                                   current_value, reason)

        # T055: is there actually a trade today? Cash is a decision, logged as one.
        no_trade: list[str] = []
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0)
        ordered_today = db.execute(
            select(func.count()).select_from(SignalLog).where(
                SignalLog.action == "ordered", SignalLog.ts >= today_start)
        ).scalar_one()
        if ordered_today >= max_trades_per_day:
            no_trade.append(
                f"overtrading guard: {ordered_today} orders already placed today "
                f"(max {max_trades_per_day}) — the biggest enemy is overtrading"
            )
        atr_frac = atr_value / last_price
        if atr_frac < eff_min_atr_frac:
            no_trade.append(
                f"expected move too small to clear costs: ATR is {atr_frac:.4%} of "
                f"price (floor {eff_min_atr_frac:.4%})"
            )
        if len(bars.bars) >= 21:  # enough history for the full regime classifier
            reading = classify_regime(
                highs, lows, closes, [b.volume for b in bars.bars],
                [b.date for b in bars.bars], volume_feed=bars.source,
            )
            if (reading.rvol is not None and reading.rvol < eff_rvol_floor
                    and reading.range_width_percentile is not None
                    and reading.range_width_percentile <= 0.25):
                no_trade.append(
                    f"quiet market: RVOL {reading.rvol:.2f} (floor {eff_rvol_floor}) "
                    f"in a bottom-quartile range width — the market is not interested "
                    f"(feed: {bars.source})"
                )
        if no_trade:
            reason = ("no trade today: " + "; ".join(no_trade)
                      + " — capital preserved by design")
            log_row("no_trade", reason, None)
            log.info("cycle NO_TRADE %s: %s", symbol, reason)
            return CycleResult("no_trade", symbol, weight, target_value,
                               current_value, reason)

        sized = volatility_parity_notional(
            acct.equity, last_price, atr_value, delta,
            risk_frac=risk.limits.risk_per_trade_frac,
            stop_atr_multiple=risk.limits.stop_atr_multiple,
        )
        if sized.binding == "risk":
            sizing_note = (
                f"vol-parity sizing bound the buy: {delta:.2f} -> "
                f"{sized.allowed_notional:.2f} (ATR {atr_value:.2f}, stop distance "
                f"{sized.stop_distance:.2f}, risk budget {sized.risk_dollars:.2f} = "
                f"{risk.limits.risk_per_trade_frac:.1%} of equity)"
            )
            delta = sized.allowed_notional
        if size_multiplier < 1.0:
            delta = delta * size_multiplier
            half_note = f"{tier_note}: buy notional halved to {delta:.2f}"
            sizing_note = f"{sizing_note}; {half_note}" if sizing_note else half_note
        elif tier_note:
            sizing_note = f"{sizing_note}; {tier_note}" if sizing_note else tier_note
    if abs(delta) < min_trade_value:
        reason = f"delta {delta:.2f} below min trade {min_trade_value:.2f}"
        if sizing_note:
            reason += f" ({sizing_note})"
        log_row("no_action", reason, None)
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
    log_row("ordered", sizing_note, placed.external_id)
    detail = f"{side} {qty} {symbol} @ ~{last_price:.2f} (order {placed.status})"
    if sizing_note:
        detail += f" — {sizing_note}"
    log.info("cycle ORDERED: %s", detail)
    return CycleResult("ordered", symbol, weight, target_value, current_value,
                       detail, placed.external_id)
