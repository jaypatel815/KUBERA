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

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from analysis.attribution import (
    attributed_fills_from_rows,
    decompose_costs,
    fifo_attribution,
)
from analysis.expected_move import expected_move
from analysis.levels import find_levels
from analysis.liquidity import spread_bps
from analysis.market_time import market_day_start_utc, market_today
from analysis.regime import classify_regime
from data.alpaca import AlpacaClient
from data.history import equity_history
from data.market_data import MarketDataClient
from data.models import SignalLog, Transaction
from risk.dqs import score_decisions
from risk.engine import RiskEngine
from risk.persistence import restore_risk_state
from risk.tiers import current_tier

PENDING_NOTES: list[str] = []  # T076b delivered the last standing note


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
    # T076b: the 5-bar runup INTO today — the priced-for-perfection input.
    out["runup_5d_frac"] = (closes[-1] / closes[-6] - 1.0
                            if len(closes) >= 6 else None)
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


def _watchlist_section(db: Session, market: MarketDataClient) -> dict:
    """T062b: top-ranked watchlist setups in the morning read (T068 ranking).
    Empty list is a normal state, said plainly."""
    from analysis.ranking import rank_watchlist
    from analysis.regime import classify_regime
    from data.watchlist import list_symbols

    entries = list_symbols(db)
    if not entries:
        return {"setups": [], "note": "watchlist is empty"}
    closes: dict[str, list[float]] = {}
    labels: dict[str, str] = {}
    for e in entries:
        bars = market.get_daily_bars(e.symbol, days=200)
        closes[e.symbol] = [b.close for b in bars.bars]
        if len(bars.bars) >= 21:
            reading = classify_regime(
                [b.high for b in bars.bars], [b.low for b in bars.bars],
                [b.close for b in bars.bars], [b.volume for b in bars.bars],
                [b.date for b in bars.bars], volume_feed=bars.source,
            )
            labels[e.symbol] = reading.regime
        else:
            labels[e.symbol] = "unknown"
    notes = {e.symbol: e.note for e in entries}
    top = [r for r in rank_watchlist(closes, labels) if r.score is not None][:3]
    return {
        "setups": [{
            "symbol": r.symbol, "score": r.score,
            "rs_percentile": r.rs_percentile, "regime": r.regime_label,
            "flags": r.flags, "thesis": notes.get(r.symbol),
        } for r in top],
        "note": None,
    }


def _events_section(fred) -> dict:
    """T062b/T076: upcoming scheduled releases. No FRED client or a calendar
    failure degrades to a note — the rest of the brief still delivers."""
    from dataclasses import asdict as _asdict

    import httpx

    from analysis.events import upcoming_events
    from analysis.fomc import fomc_staleness_note, with_fomc
    from data.fred import FredError

    today = market_today()  # T111: market day
    stale = fomc_staleness_note(today)
    if fred is None:
        # T076b: the FOMC table needs no key — decision days still guard.
        events = upcoming_events(with_fomc(None), today)
        return {"upcoming": [_asdict(e) for e in events],
                "note": "CPI/NFP calendar off (add FRED_API_KEY to .env); "
                        "FOMC dates from the published table" +
                        (f" | {stale}" if stale else "")}
    try:
        events = upcoming_events(with_fomc(fred.release_calendar()), today)
        return {"upcoming": [_asdict(e) for e in events], "note": stale}
    except (FredError, httpx.HTTPError) as e:
        events = upcoming_events(with_fomc(None), today)
        return {"upcoming": [_asdict(e) for e in events],
                "note": f"CPI/NFP calendar unavailable: {e}; FOMC dates from "
                        "the published table" + (f" | {stale}" if stale else "")}


def _earnings_section(fmp, held_symbols: set[str], horizon_days: int = 14, db=None) -> dict:
    """T023: upcoming earnings for HELD symbols. No FMP client (or any failure)
    degrades to a note — an earnings date the brief cannot fetch must never
    become an earnings date the brief pretends does not exist silently."""
    if fmp is None:
        return {"upcoming": [],
                "note": "earnings calendar off (add FMP_API_KEY to .env — free tier works)"}
    import httpx

    from data.fmp import FmpError
    try:
        today = market_today()  # T111: at 11 PM ET, UTC is already tomorrow
        cal = fmp.earnings_calendar(today, today + timedelta(days=horizon_days))
        # T083: feed the observed-history store — every morning brief grows
        # the past that the paywalled FMP windows cannot supply.
        from data.earnings_store import record_calendar
        record_calendar(db, cal)
        mine = [
            {"symbol": e.symbol, "date": e.date.isoformat(),
             "time_hint": e.time_hint, "eps_estimated": e.eps_estimated}
            for e in cal.events if e.symbol in held_symbols
        ]
        note = None
        if cal.unparsed:
            note = f"{len(cal.unparsed)} calendar rows unparseable (reported, not dropped)"
        return {"upcoming": mine, "horizon_days": horizon_days, "note": note}
    except (FmpError, httpx.HTTPError) as e:
        return {"upcoming": [], "note": f"earnings calendar unavailable: {e}"}


def _base_rates_summary(db: Session | None, market: MarketDataClient,
                        symbol: str) -> dict:
    """T083c — a COMPACT hold-through-earnings read for one held symbol.

    Full detail lives in the get_event_base_rates tool; the brief carries the
    headline: how many past reactions are on record, the median event-day
    move, and how often the reaction day closed down. Degrades to a why —
    a missing history is information, not an error (the T062 rule)."""
    if db is None:
        return {"available": False, "why": "no db in this brief context"}
    from datetime import date as _date

    from analysis.event_rates import MIN_EVENTS, compute_event_base_rates
    from data.earnings_store import stored_events
    try:
        rows = stored_events(db, symbol)
        today = market_today()
        past = [type("E", (), {
            "date": _date.fromisoformat(r.event_date),
            "time_hint": r.time_hint,
            "eps_actual": r.eps_actual,
            "eps_estimated": r.eps_estimated,
        })() for r in rows if _date.fromisoformat(r.event_date) <= today]
        if len(past) < MIN_EVENTS:
            return {"available": False,
                    "why": f"{len(past)} observed past reaction(s) — base "
                           f"rates need {MIN_EVENTS} (EDGAR backfills on the "
                           "next get_event_base_rates call)"}
        bars = market.get_daily_bars(symbol, days=800)
        rates = compute_event_base_rates(
            symbol, past,
            [_date.fromisoformat(str(b.date)[:10]) for b in bars.bars],
            [b.close for b in bars.bars])
        if rates.verdict != "rates":
            return {"available": False, "why": rates.note}
        from statistics import median as _median
        moves = [r.event_day_move for r in rates.reactions]
        down = sum(1 for m in moves if m < 0)
        mid = _median(moves)
        return {
            "available": True,
            "events_measured": rates.events_measured,
            "median_event_day_move": round(mid, 4),
            "closed_down_frac": round(down / len(moves), 3),
            "note": "base rates from this symbol's own history — description "
                    "of the past, not a prediction (full split: "
                    "get_event_base_rates)",
        }
    except Exception as e:  # the brief never dies for a base-rates problem
        return {"available": False,
                "why": f"base rates unavailable ({type(e).__name__})"}


def compose_morning_brief(db: Session, alpaca: AlpacaClient,
                          market: MarketDataClient, fred=None, fmp=None) -> dict:
    acct = alpaca.get_account()
    positions = alpaca.get_positions()
    held = {p.symbol for p in positions}
    symbols = sorted(held | {"SPY"})
    symbol_reads = [_symbol_read(market, s) for s in symbols]
    earnings = _earnings_section(fmp, held, db=db)

    # T076b: the priced-for-perfection join (D019). A held symbol reporting
    # soon whose 5-bar runup already meets its own p95 expected 5-day move
    # has paid for good news in advance — flagged, never predicted.
    from analysis.fomc import priced_for_perfection
    reads_by_symbol = {r["symbol"]: r for r in symbol_reads if r.get("available")}
    for entry in earnings.get("upcoming", []):
        read = reads_by_symbol.get(entry["symbol"])
        if read is None:
            continue
        em = read.get("expected_move_5d") or {}
        entry["priced_for_perfection"] = priced_for_perfection(
            read.get("runup_5d_frac"), em.get("p95"))
        # T083c: how THIS symbol historically reacted to earnings — base
        # rates from the observed store (EDGAR + accumulated FMP dates).
        entry["base_rates"] = _base_rates_summary(db, market, entry["symbol"])

    return {
        "type": "morning",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "account": {"equity": acct.equity, "cash": acct.cash, "asof": acct.asof.isoformat()},
        "risk": _risk_section(db, acct.equity),
        "symbols": symbol_reads,
        "watchlist": _watchlist_section(db, market),
        "event_risk": _events_section(fred),
        "earnings_risk": earnings,
        "notes": PENDING_NOTES,
        "source": acct.source,
    }


def compose_eod_report(db: Session, alpaca: AlpacaClient) -> dict:
    acct = alpaca.get_account()
    risk = _risk_section(db, acct.equity)
    day_start = risk["day_start_equity"]
    # T111: the EOD report's day is the MARKET day. With a UTC boundary, an
    # evening EOD run (after 8 PM ET) reported an empty day — every decision of
    # the afternoon sat before UTC midnight.
    today = market_day_start_utc()
    rows = db.execute(
        select(SignalLog).where(SignalLog.ts >= today).order_by(SignalLog.ts)
    ).scalars().all()
    counts: dict[str, int] = {}
    for r in rows:
        counts[r.action] = counts.get(r.action, 0) + 1

    # T091b: the day's decisions BY THE REGIME they were made in — every row has
    # carried its regime stamp since T091, so this is a regroup, not a guess.
    by_regime: dict[str, dict[str, int]] = {}
    for r in rows:
        slot = by_regime.setdefault(r.regime_label or "untagged", {})
        slot[r.action] = slot.get(r.action, 0) + 1
    dominant = max(by_regime, key=lambda k: sum(by_regime[k].values())) if by_regime else None
    regime_attribution = {
        "by_regime": by_regime,
        "dominant_regime": dominant,
        "note": ("today's decisions grouped by the regime read AT DECISION TIME "
                 "(T091 stamps); day P&L sits in `account.day_pl_frac` beside it — "
                 "attribution of P&L to regime needs closed round trips, which the "
                 "weekly review carries"),
    }
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
        "regime_attribution": regime_attribution,
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

    # T091b: the investment-committee half the review was missing — WHERE the
    # realized P&L actually came from (regime, holding period), plus the T090
    # spread-cost estimate. All from recorded fills; degrades to a plain "why".
    tags_by_order = {
        r.order_external_id: (r.regime_label, r.sub_strategy, r.entry_bucket)
        for r in rows if r.order_external_id
    }
    txns = db.execute(select(Transaction).order_by(Transaction.occurred_at)).scalars().all()
    if txns:
        rep = fifo_attribution(attributed_fills_from_rows(txns, tags_by_order))
        hp = rep.holding_periods or {}
        regimes_with_trips = {k: v for k, v in rep.by_regime.items()
                              if v["round_trips"] > 0}
        best = max(regimes_with_trips, key=lambda k: regimes_with_trips[k]["realized_pnl"],
                   default=None)
        worst = min(regimes_with_trips, key=lambda k: regimes_with_trips[k]["realized_pnl"],
                    default=None)
        costs = None
        try:
            half_by_symbol: dict[str, float] = {}
            for sym in sorted({t["symbol"] for t in rep.trips}):
                q = market.get_latest_quote(sym)
                if q.bid > 0 and q.ask > 0:
                    half_by_symbol[sym] = spread_bps(q.bid, q.ask) / 2.0
            costs = decompose_costs(rep.trips, half_by_symbol)
        except Exception:  # noqa: BLE001 — cost estimate is optional context
            costs = None
        attribution = {
            "available": True,
            "round_trips": rep.round_trips,
            "realized_pnl": round(rep.realized_pnl, 2),
            "by_regime": rep.by_regime,
            "holding_periods": hp,
            "best_regime": best,
            "worst_regime": worst,
            "cost_decomposition": costs,
        }
        if rep.round_trips:
            med = hp.get("median_days")
            facts.append(
                f"{rep.round_trips} closed round trips realized "
                f"${rep.realized_pnl:,.2f}"
                + (f"; median hold {med:g} days" if med is not None else "")
            )
            if best and worst and best != worst:
                facts.append(
                    f"best regime {best} (${regimes_with_trips[best]['realized_pnl']:,.2f}), "
                    f"worst {worst} (${regimes_with_trips[worst]['realized_pnl']:,.2f}) — "
                    f"counts: {regimes_with_trips[best]['round_trips']} vs "
                    f"{regimes_with_trips[worst]['round_trips']}"
                )
            if costs and costs["total_est_spread_cost"] > 0:
                facts.append(
                    f"estimated spread cost ${costs['total_est_spread_cost']:,.2f} "
                    "(at today's spreads — an estimate, never netted into P&L)"
                )
    else:
        attribution = {"available": False,
                       "why": "no recorded fills yet — run scripts/sync.py after trading"}

    # T063b: calibration v2 — was stated confidence honest, did plans pay
    # their planned R, and how did overridden calls resolve? Best-effort:
    # the review composes even if prices or the journal are unavailable.
    try:
        from dataclasses import asdict as _asdict

        from analysis.calibration import compute_calibration
        from data.journal import list_decisions
        jrows = list_decisions(db, limit=200)
        _cache: dict[str, float | None] = {}

        def _px(sym: str) -> float | None:
            if sym not in _cache:
                try:
                    _cache[sym] = market.get_latest_trade(sym).price
                except Exception:  # noqa: BLE001 — one dead symbol, not the review
                    _cache[sym] = None
            return _cache[sym]

        cal = compute_calibration(jrows, price_lookup=_px)
        journal_calibration = {"available": True, **_asdict(cal)}
        if cal.weighted_gap is not None:
            facts.append(
                f"confidence calibration gap {cal.weighted_gap:+.2f} over "
                f"{cal.n_evaluable} aged decisions "
                "(positive = underconfident, negative = overconfident)")
        ov = cal.override.get("overridden", {})
        if ov.get("hit_rate") is not None:
            facts.append(
                f"decisions you overrode were right {ov['hit_rate']:.0%} of "
                f"the time (n={ov['n']}) — measurement, not a scolding")
    except Exception as e:  # noqa: BLE001 — calibration is optional context
        journal_calibration = {"available": False,
                               "why": f"{type(e).__name__}: {e}"}

    return {
        "type": "weekly",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "performance": performance,
        "attribution": attribution,
        "journal_calibration": journal_calibration,
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
