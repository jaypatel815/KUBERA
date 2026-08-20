"""T087c — the monitor's fetch-and-judge half as a SHARED service.

scripts/monitor.py (the owner's terminal) and GET /api/monitor (the future
Orb panel) must never drift: two surfaces, ONE implementation. The fetch
composition here is moved VERBATIM from the T087a script — same regime /
levels / breakout / exit-plan assembly the get_exit_plan tool uses, same
named degradations, same I033 lens discipline (the days lens leads, the
structural label carries its timeframe, week-to-date prints beside it).

The api/brief.py precedent: composition shared by an endpoint and a CLI
lives here in backend/api/, importable from both sides.

ADVISORY ONLY — nothing in this module places, cancels, or resizes
anything. Missing inputs become NAMED notes on the check, never crashes:
a monitor that dies mid-session is worse than one that says what it
couldn't see.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from analysis.breakout import detect_breakouts
from analysis.events import entry_guard
from analysis.exit_plan import build_exit_plan
from analysis.fomc import with_fomc
from analysis.intraday import build_session_read
from analysis.levels import find_levels
from analysis.market_time import market_today
from analysis.metrics import atr
from analysis.monitor import (
    MonitorSummary,
    PositionCheck,
    check_position,
    describe_regime,
    summarize,
)
from analysis.regime import classify_regime
from analysis.short_horizon import one_line, short_horizon_read
from data.market_data import MarketDataClient, MarketDataError
from settings import KuberaSettings, get_settings


def open_event_windows(
    settings: KuberaSettings | None = None,
) -> tuple[list[str], str | None]:
    """Names of scheduled-event guard windows open today, plus a degradation
    note when the FRED calendar could not be read (the note is DATA now —
    each surface decides where to print it). FRED is optional; the FOMC
    table needs no key, so a degraded calendar still guards FOMC days."""
    dates, note = None, None
    try:
        s = settings if settings is not None else get_settings()
        if s.fred_api_key:
            from data.fred import FredClient

            with FredClient(settings=s) as fred:
                dates = fred.release_calendar()
    except Exception as e:  # noqa: BLE001 — the calendar is context, not the job
        note = f"{type(e).__name__}: {e}"
    return entry_guard(with_fomc(dates), market_today()), note


def check_symbol(
    market: MarketDataClient, symbol: str, windows: list[str]
) -> tuple[PositionCheck, str]:
    """One position's full read: (judged check, days-lens line). Moved
    verbatim from scripts/monitor.py — the composition the owner already
    runs, now also servable."""
    bars = market.get_daily_bars(symbol, days=250)
    closes = [b.close for b in bars.bars]
    highs = [b.high for b in bars.bars]
    lows = [b.low for b in bars.bars]
    dates = [b.date for b in bars.bars]

    regime = None
    plan_level, plan_reason = None, "no exit plan (thin history)"
    atr_value = None
    if len(bars.bars) >= 21:
        volumes = [b.volume for b in bars.bars]
        reading = classify_regime(highs, lows, closes, volumes, dates,
                                  volume_feed=bars.source)
        regime = reading.regime
        atr_value = atr(highs, lows, closes) if len(bars.bars) >= 15 else None
        levels = find_levels(highs, lows, closes, dates)
        boundary = direction = None
        scan = detect_breakouts(highs, lows, closes, volumes, dates)
        if scan.active and scan.latest is not None:
            boundary, direction = scan.latest.boundary, scan.latest.direction
        # same composition the get_exit_plan tool uses (T056)
        plan = build_exit_plan(
            reading.regime, closes[-1],
            atr_value=atr_value,
            support=(levels.nearest_support.price
                     if levels.nearest_support else None),
            resistance=(levels.nearest_resistance.price
                        if levels.nearest_resistance else None),
            sma=reading.sma,
            breakout_boundary=boundary,
            breakout_direction=direction,
        )
        plan_level = plan.invalidation_level
        plan_reason = plan.invalidation_reason

    price = None
    try:
        price = market.get_latest_trade(symbol).price
    except (MarketDataError, httpx.HTTPError):
        pass  # named inside check_position as a blind spot

    session_rvol, crossings, used = None, None, 0
    try:
        five = market.get_intraday_bars(symbol, timeframe="5Min", days=9)
        if five.bars:
            s = build_session_read(five.bars, volume_feed=five.source)
            session_rvol, used = s.intraday_rvol, s.rvol_sessions_used
            crossings = s.vwap_crossings
    except (MarketDataError, ValueError, httpx.HTTPError):
        pass  # named inside check_position

    # I033: the short lens, computed here so it surfaces BESIDE the label.
    week_change = (closes[-1] / closes[-6] - 1.0) if len(closes) >= 6 else None

    # T116/D035: the DAYS lens leads — computed from the same closes.
    # T116b: FOMC dates (keyless table) become caveats when inside the
    # window; the monitor already guards TODAY's windows separately.
    days_line = one_line(short_horizon_read(symbol, closes, dates,
                                            upcoming=with_fomc(None)))

    return check_position(
        symbol, price,
        daily_regime=regime,
        session_rvol=session_rvol, rvol_sessions_used=used,
        vwap_crossings=crossings,
        invalidation_level=plan_level, invalidation_reason=plan_reason,
        atr_value=atr_value,
        open_event_windows=windows,
        week_change_frac=week_change,
    ), days_line


@dataclass(frozen=True)
class PositionRead:
    symbol: str
    qty: float
    unrealized_plpc: float
    days_line: str            # D035: the days lens, always first
    check: PositionCheck


@dataclass(frozen=True)
class MonitorRun:
    asof_utc: str
    positions: list[PositionRead]
    summary: MonitorSummary
    calendar_note: str | None  # named degradation of the event calendar


def run_monitor(
    alpaca, market: MarketDataClient, *,
    settings: KuberaSettings | None = None,
    windows: list[str] | None = None,
) -> MonitorRun:
    """One full monitor pass over held positions. `windows` may be injected
    (tests / callers that already fetched); None means fetch — and, as in
    the CLI since T087a, the calendar is only consulted when something is
    actually held."""
    asof = datetime.now(timezone.utc).isoformat()
    positions = alpaca.get_positions()
    if not positions:
        return MonitorRun(asof, [], summarize([]), None)
    note = None
    if windows is None:
        windows, note = open_event_windows(settings)
    reads = []
    for pos in positions:
        check, days_line = check_symbol(market, pos.symbol, windows)
        reads.append(PositionRead(
            symbol=pos.symbol, qty=pos.qty,
            unrealized_plpc=pos.unrealized_plpc,
            days_line=days_line, check=check,
        ))
    return MonitorRun(asof, reads, summarize([r.check for r in reads]), note)


def run_payload(run: MonitorRun) -> dict:
    """The MonitorRun as an explicit, lens-labeled payload — what the
    endpoint returns and any panel renders. Every judgment field the CLI
    prints is here, including the I033 explainer for the exact case that
    confused the owner's first live run."""
    positions = []
    for r in run.positions:
        c = r.check
        context_note = None
        if c.regime == "trending_up" and (c.week_change_frac or 0.0) < 0:
            context_note = (
                "a red week inside a structural uptrend is normal — "
                "the session alerts are the today lens"
            )
        positions.append({
            "symbol": c.symbol,
            "qty": r.qty,
            "unrealized_plpc": r.unrealized_plpc,
            "days_lens": r.days_line,
            "regime": c.regime,
            "structure": describe_regime(c.regime),
            "week_change_frac": c.week_change_frac,
            "price": c.price,
            "context_note": context_note,
            "alerts": [
                {"severity": a.severity, "kind": a.kind, "detail": a.detail}
                for a in c.alerts
            ],
            "blind_spots": list(c.notes),
            "quiet": not c.alerts and not c.notes,
        })
    s = run.summary
    return {
        "asof_utc": run.asof_utc,
        "advisory": s.note,
        "calendar_note": run.calendar_note,
        "positions": positions,
        "summary": {
            "positions": s.positions,
            "alerts": s.alerts,
            "watches": s.watches,
            "blind_spots": s.blind_spots,
            "needs_eyes_now": s.exit_code == 1,
        },
    }
