"""T087a — open-trade monitor v1 (advisory CLI). Owner usage, during RTH:

    python scripts\\monitor.py                # one pass over held positions
    python scripts\\monitor.py --loop 300     # every 5 minutes until Ctrl+C
    python scripts\\monitor.py --loop 300 --notify   # + Windows toast on alerts

Per held position: the daily regime, session RVOL + VWAP churn (T052), the
exit plan's invalidation level (T056) against the LIVE price, and any open
scheduled-event window (T076/T076b). Exit codes are schedulable: 1 = at
least one position needs eyes NOW (pair with Task Scheduler; the toast
pattern lives in scripts\\health_check.py), 0 = watched, nothing burning,
2 = not configured / broker-data unreachable (named).

ADVISORY ONLY — this script never places, cancels, or resizes anything.
Voice barge-in + Orb surface remain T074/T087. Weekends/after hours it
still runs: intraday reads degrade to NAMED notes instead of failing.
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import httpx  # noqa: E402
from notify import notify_windows  # noqa: E402

from analysis.breakout import detect_breakouts  # noqa: E402
from analysis.events import entry_guard  # noqa: E402
from analysis.exit_plan import build_exit_plan  # noqa: E402
from analysis.fomc import with_fomc  # noqa: E402
from analysis.intraday import build_session_read  # noqa: E402
from analysis.levels import find_levels  # noqa: E402
from analysis.market_time import market_today  # noqa: E402
from analysis.metrics import atr  # noqa: E402
from analysis.monitor import (  # noqa: E402
    MonitorAlert,
    PositionCheck,
    check_position,
    describe_regime,
    summarize,
)
from analysis.regime import classify_regime  # noqa: E402
from analysis.short_horizon import one_line, short_horizon_read  # noqa: E402
from data.alpaca import AlpacaClient, AlpacaError  # noqa: E402
from data.market_data import MarketDataClient, MarketDataError  # noqa: E402
from settings import ConfigError, get_settings  # noqa: E402


def _open_event_windows() -> list[str]:
    """Names of scheduled-event guard windows open today. FRED is optional;
    the FOMC table needs no key. Failure degrades to empty + stderr note."""
    dates = None
    try:
        settings = get_settings()
        if settings.fred_api_key:
            from data.fred import FredClient
            with FredClient(settings=settings) as fred:
                dates = fred.release_calendar()
    except Exception as e:  # noqa: BLE001 — the calendar is context, not the job
        print(f"  (event calendar degraded: {type(e).__name__}: {e})",
              file=sys.stderr)
    return entry_guard(with_fomc(dates), market_today())


def _check_symbol(market: MarketDataClient, symbol: str,
                  windows: list[str]) -> "tuple[PositionCheck, str]":
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

    # I033: the short lens, computed here so it prints BESIDE the label.
    week_change = (closes[-1] / closes[-6] - 1.0) if len(closes) >= 6 else None

    # T116/D035: the DAYS lens leads — computed from the same closes.
    days_line = one_line(short_horizon_read(symbol, closes, dates))

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


def _print_alert(a: MonitorAlert) -> None:
    flag = "!!" if a.severity == "alert" else " ~"
    print(f"  {flag} [{a.kind}] {a.detail}")


def run_once(notify: bool = False) -> int:
    try:
        get_settings().require_alpaca()
    except ConfigError as e:
        print(f"NOT CONFIGURED\n  {e}")
        return 2
    try:
        with AlpacaClient() as alpaca, MarketDataClient() as market:
            positions = alpaca.get_positions()
            if not positions:
                print("no open positions — nothing to monitor (that is an "
                      "answer, not an error)")
                return 0
            windows = _open_event_windows()
            checks = []
            for pos in positions:
                print(f"{pos.symbol}  qty {pos.qty:g}  "
                      f"uP&L {pos.unrealized_plpc:+.2%}")
                c, days_line = _check_symbol(market, pos.symbol, windows)
                checks.append(c)
                print(f"  {days_line}")            # the days lens leads (D035)
                week = (f"{c.week_change_frac:+.2%}"
                        if c.week_change_frac is not None else "?")
                print(f"  structure: {describe_regime(c.regime)}")
                line = (f"  this week: {week}   price: "
                        f"{c.price if c.price is not None else '?'}")
                if c.regime == "trending_up" and \
                        (c.week_change_frac or 0.0) < 0:
                    # I033: the exact case that confused the owner's first
                    # run — say it right where the two lenses meet.
                    line += ("   (a red week inside a structural uptrend is "
                             "normal — the session lines below are the "
                             "today lens)")
                print(line)
                for a in c.alerts:
                    _print_alert(a)
                for n in c.notes:
                    print(f"   . blind spot: {n}")
                if not c.alerts and not c.notes:
                    print("   . quiet — plan intact, volume normal")
    except (AlpacaError, MarketDataError, httpx.HTTPError) as e:
        print(f"BROKER/DATA UNREACHABLE — no monitor pass\n"
              f"  {type(e).__name__}: {e}")
        return 2

    s = summarize(checks)
    print("-" * 70)
    print(f"{s.positions} position(s): {s.alerts} alert(s), "
          f"{s.watches} watch(es), {s.blind_spots} named blind spot(s)")
    print(s.note)
    if notify and s.alerts:
        # T087b: tap on the shoulder — the FIRST alert rides in the toast;
        # the terminal (and the exit code) carry the full story.
        first = next(a for c in checks for a in c.alerts
                     if a.severity == "alert")
        notify_windows(f"KUBERA monitor: {s.alerts} alert(s)",
                       f"{first.symbol} [{first.kind}] {first.detail}")
    return s.exit_code


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Open-trade monitor (T087a) — advisory only.")
    ap.add_argument("--loop", type=int, default=0, metavar="SECONDS",
                    help="repeat every N seconds (0 = run once)")
    ap.add_argument("--notify", action="store_true",
                    help="Windows toast when something needs eyes (best-effort)")
    args = ap.parse_args()
    if args.loop <= 0:
        return run_once(notify=args.notify)
    while True:
        code = run_once(notify=args.notify)
        if code == 2:
            return code  # config/broker problems don't fix themselves in a loop
        time.sleep(args.loop)


if __name__ == "__main__":
    sys.exit(main())
