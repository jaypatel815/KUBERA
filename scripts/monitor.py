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

from analysis.monitor import MonitorAlert, describe_regime, summarize  # noqa: E402
from api.monitor_service import check_symbol, open_event_windows  # noqa: E402
from data.alpaca import AlpacaClient, AlpacaError  # noqa: E402
from data.market_data import MarketDataClient, MarketDataError  # noqa: E402
from settings import ConfigError, get_settings  # noqa: E402

# T087c: the fetch-and-judge half moved VERBATIM to api/monitor_service.py,
# shared with GET /api/monitor — two surfaces, one implementation. This
# script keeps only the terminal half: progressive printing (a human is
# watching it fetch), toasts, and schedulable exit codes.


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
            windows, cal_note = open_event_windows(get_settings())
            if cal_note:
                print(f"  (event calendar degraded: {cal_note})",
                      file=sys.stderr)
            checks = []
            for pos in positions:
                print(f"{pos.symbol}  qty {pos.qty:g}  "
                      f"uP&L {pos.unrealized_plpc:+.2%}")
                c, days_line = check_symbol(market, pos.symbol, windows)
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
