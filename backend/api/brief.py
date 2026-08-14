"""Briefs & reviews (T062, D016/D018) — deterministic composition, LLM narration.

Three compositions, all facts-with-timestamps, zero LLM arithmetic:
- morning: market regime + per-holding overnight gaps, regime, expected move,
  nearest levels — "what does the day look like before the open".
- eod: today's decisions from signal_log (ordered / rejected / no_trade with
  reasons), risk-budget consumption + tier, DQS — "what did we do and how well".
- weekly: the investment-committee review — equity vs SPY over the week,
  discipline counts, deterministic FACTS for the narrator to draw lessons from
  (the LLM narrates lessons; it never invents numbers).

Sections DEGRADE GRACEFULLY: missing history yields {"available": False, "why"}
instead of failing the whole brief — a brief with a gap in it is still a brief,
and the gap itself is information. Watchlist setups arrive with T068; event risk
with T076 — noted in the payload so the narrator can say so honestly.

Voice-ready: ask the Orb "give me my morning brief" — the chat layer calls the
get_brief tool and narrates this structure per VOICE_STYLE.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from analysis.expected_move import expected_move
from analysis.levels import find_levels
from analysis.regime import classify_regime
from data.alpaca import AlpacaClient
from data.history import equity_history
from data.market_data import MarketDataClient
from data.models import SignalLog
from risk.dqs import score_decisions
from risk.engine import RiskEngine
from risk.persistence import restore_risk_state
from risk.tiers import current_tier

PENDING_NOTES = [
    "watchlist setups arrive with T068",
    "economic-event risk arrives with T076",
]


def _risk_section(db: Session, equity: float) -> dict:
    engine = RiskEngine()
    restore_risk_state(db, engine)
    tier = None
    if engine.day_start_equity is not None:
        t = current_tier(engine.day_start_equity, equity,
                         engine.limits.daily_loss_limit_frac)
        tier = {"level": t.level, "name": t.name,
                "budget_consumed_frac": t.budget_consumed_frac}
    rows = db.execute(select(SignalLog)).scalars().all()
    dqs = score_decisions(rows)
    return {
        "day_start_equity": engine.day_start_equity,
        "tier": tier,
        "breaker": {"tripped": engine.tripped, "reason": engine.trip_reason},
        "dqs": {"score": dqs.score, "orders": dqs.orders, "no_trades": dqs.no_trades},
    }


def _symbol_read(market: MarketDataClient, symbol: str) -> dict:
    bars = market.get_daily_bars(symbol, days=250)
    if len(bars.bars) < 2:
        return {"symbol": symbol, "available": False, "why": "no price history"}
    closes = [b.close for b in bars.bars]
    highs = [b.high for b in bars.bars]
    lows = [b.low for b in bars.bars]
    dates = [b.date for b in bars.bars]
    last_close = closes[-1]

    trade = market.get_latest_trade(symbol)
    out: dict = {
        "symbol": symbol,
        "available": True,
        "last_close": last_close,
        "last_close_date": dates[-1],
        "latest_price": trade.price,
        "latest_age_seconds": trade.age_seconds,
        "latest_stale": trade.stale,
        "overnight_gap_frac": trade.price / last_close - 1.0,
    }
    if len(bars.bars) >= 21:
        r = classify_regime(highs, lows, closes, [b.volume for b in bars.bars],
                            dates, volume_feed=bars.source)
        out["regime"] = {"regime": r.regime, "confidence": r.confidence,
                        "reason": r.reason}
        levels = find_levels(highs, lows, closes, dates)
        out["nearest_support"] = (
            {"price": levels.nearest_support.price,
             "touches": levels.nearest_support.touches}
            if levels.nearest_support else None)
        out["nearest_resistance"] = (
            {"price": levels.nearest_resistance.price,
             "touches": levels.nearest_resistance.touches}
            if levels.nearest_resistance else None)
    else:
        out["regime"] = None
    try:
        em = expected_move(closes, dates, horizon_days=5)
        out["expected_move_5d"] = {
            "p05": em.unconditional.percentiles["p05"],
            "p95": em.unconditional.percentiles["p95"],
            "up_frac": em.unconditional.up_frac,
        }
    except ValueError:
        out["expected_move_5d"] = None
    return out


def compose_morning_brief(db: Session, alpaca: AlpacaClient,
                          market: MarketDataClient) -> dict:
    acct = alpaca.get_account()
    positions = alpaca.get_positions()
    symbols = sorted({p.symbol for p in positions} | {"SPY"})
    return {
        "type": "morning",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "account": {"equity": acct.equity, "cash": acct.cash, "asof": acct.asof.isoformat()},
        "risk": _risk_section(db, acct.equity),
        "symbols": [_symbol_read(market, s) for s in symbols],
        "notes": PENDING_NOTES,
        "source": acct.source,
    }


def compose_eod_report(db: Session, alpaca: AlpacaClient) -> dict:
    acct = alpaca.get_account()
    risk = _risk_section(db, acct.equity)
    day_start = risk["day_start_equity"]
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0,
                                               microsecond=0)
    rows = db.execute(
        select(SignalLog).where(SignalLog.ts >= today).order_by(SignalLog.ts)
    ).scalars().all()
    counts: dict[str, int] = {}
    for r in rows:
        counts[r.action] = counts.get(r.action, 0) + 1
    return {
        "type": "eod",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "account": {
            "equity": acct.equity,
            "day_start_equity": day_start,
            "day_pl_frac": (acct.equity / day_start - 1.0) if day_start else None,
            "asof": acct.asof.isoformat(),
        },
        "risk": risk,
        "activity": {
            "counts": counts,
            "decisions": [
                {"ts": r.ts.isoformat(), "strategy": r.strategy, "symbol": r.symbol,
                 "action": r.action, "reasons": r.reasons}
                for r in rows
            ],
        },
        "source": acct.source,
    }


def compose_weekly_review(db: Session, alpaca: AlpacaClient,
                          market: MarketDataClient) -> dict:
    acct = alpaca.get_account()
    points = equity_history(db, days=7)
    if len(points) >= 2:
        eq_start, eq_end = points[0][1], points[-1][1]
        performance: dict = {
            "available": True,
            "period": {"start": points[0][0], "end": points[-1][0]},
            "equity_start": eq_start,
            "equity_end": eq_end,
            "return_frac": eq_end / eq_start - 1.0,
        }
        try:
            bars = market.get_daily_bars("SPY", days=14)
            spy = [(b.date, b.close) for b in bars.bars
                   if points[0][0] <= b.date <= points[-1][0]]
            if len(spy) >= 2:
                spy_return = spy[-1][1] / spy[0][1] - 1.0
                performance["benchmark"] = {
                    "symbol": "SPY", "return_frac": spy_return,
                    "excess_return_frac": performance["return_frac"] - spy_return,
                }
        except Exception:  # noqa: BLE001 — benchmark is optional context
            performance["benchmark"] = None
    else:
        performance = {"available": False,
                       "why": "fewer than 2 daily snapshots — run scripts/sync.py daily"}

    week_ago = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0,
                                                  microsecond=0)
    rows = db.execute(select(SignalLog).order_by(SignalLog.ts)).scalars().all()
    dqs = score_decisions(rows)
    ordered = [r for r in rows if r.action == "ordered"]
    no_trades = [r for r in rows if r.action == "no_trade"]
    rejected = [r for r in rows if r.action == "rejected"]
    tier_notes = sum(1 for r in rows if r.reasons and "risk tier" in r.reasons)
    _ = week_ago  # window handling lives in score_decisions; rows shown in full

    facts = [
        f"{len(ordered)} orders, {len(no_trades)} deliberate no-trade decisions, "
        f"{len(rejected)} risk rejections in the log",
        f"decision quality score {dqs.score} over the last {dqs.window_days} days",
    ]
    if tier_notes:
        facts.append(f"risk tiers restricted entries {tier_notes} time(s)")
    if performance.get("available"):
        facts.append(f"equity moved {performance['return_frac']:+.2%} over the period")

    return {
        "type": "weekly",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "performance": performance,
        "discipline": {
            "dqs": {"score": dqs.score, "components": dqs.components},
            "orders": len(ordered), "no_trades": len(no_trades),
            "rejected": len(rejected), "tier_restrictions": tier_notes,
        },
        "facts_for_lessons": facts,
        "narration_rule": ("lessons and next priorities are narrated from these "
                           "facts only — never invent numbers"),
        "source": acct.source,
    }
