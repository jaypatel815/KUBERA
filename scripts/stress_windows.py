"""T064b-rest — run a strategy through the named crisis windows. Owner CLI:

    python scripts\\stress_windows.py momentum SPY
    python scripts\\stress_windows.py regime_router SPY --cost-bps 5

Re-runs the template over covid-2020 and bear-2022 beside a buy-and-hold
of the SAME window, each also at 2x costs (T109b). 2008 prints as
IMPOSSIBLE on this feed by name — never silently substituted. Windows the
feed doesn't fully cover REFUSE with the feed's first date (a partial
crash is an easier test, not the same test).

MEASUREMENT ONLY: nothing is recorded; promotion/demotion are untouched.
The sandbox cannot reach the data host — this runs on the owner's machine;
unreachable feed prints a named degradation and exits 2.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import httpx  # noqa: E402

from backtest.strategies import TEMPLATES  # noqa: E402
from backtest.stress import (  # noqa: E402
    IMPOSSIBLE_WINDOWS,
    WINDOWS,
    CoverageError,
    stress_template,
)
from data.market_data import MarketDataClient, MarketDataError  # noqa: E402
from settings import ConfigError, get_settings  # noqa: E402


def _fmt(run) -> str:
    sharpe = f"{run.sharpe_ann:+.2f}" if run.sharpe_ann is not None else "  n/a"
    return (f"ret {run.cumulative_return:+8.2%}  maxDD {run.max_drawdown_frac:7.2%}  "
            f"sharpe {sharpe}  rebal {run.n_rebalances:3d}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Crisis-window stress runs (T064b) — measurement only.")
    ap.add_argument("strategy", choices=sorted(TEMPLATES))
    ap.add_argument("symbol", nargs="?", default="SPY")
    ap.add_argument("--cost-bps", type=float, default=5.0)
    args = ap.parse_args()

    try:
        get_settings().require_alpaca()
    except ConfigError as e:
        print(f"NOT CONFIGURED\n  {e}")
        return 2

    symbol = args.symbol.upper()
    print(f"Crisis-window stress: {args.strategy} on {symbol} "
          f"(cost {args.cost_bps:g} bps; every row also shown at 2x)")
    print("-" * 78)

    try:
        with MarketDataClient() as market:
            bars = market.get_daily_bars(symbol, days=3650)
    except (MarketDataError, httpx.HTTPError) as e:
        print(f"FEED UNREACHABLE — no stress run\n  {type(e).__name__}: {e}")
        return 2

    dates = [str(b.date)[:10] for b in bars.bars]
    closes = [b.close for b in bars.bars]
    print(f"history: {len(closes)} bars, {dates[0]}..{dates[-1]} "
          f"({bars.source})\n")

    failures = 0
    for window in WINDOWS:
        print(f"{window.name}  [{window.start}..{window.end}] — {window.why}")
        try:
            rep = stress_template(args.strategy, symbol, dates, closes,
                                  window, cost_bps=args.cost_bps)
        except CoverageError as e:
            failures += 1
            print(f"  NOT MEASURED: {e}\n")
            continue
        print(f"  {args.strategy:<16} {_fmt(rep.strategy)}")
        print(f"  {'  at 2x costs':<16} {_fmt(rep.strategy_2x_cost)}")
        print(f"  {'buy_and_hold':<16} {_fmt(rep.buy_and_hold)}")
        saved = rep.drawdown_saved_frac
        verdict = ("protected" if saved > 0.02
                   else "tracked the crash" if saved > -0.02 else "did WORSE")
        print(f"  drawdown vs holding: {saved:+.2%} ({verdict}; "
              f"{rep.bars} bars {rep.first_date}..{rep.last_date})\n")

    for name, why in IMPOSSIBLE_WINDOWS:
        print(f"{name}  IMPOSSIBLE ON THIS FEED — {why}")

    print("-" * 78)
    print("Measurement only: nothing recorded; promotion (T064) and demotion")
    print("(T093 CUSUM) are untouched. Rerun any time — it is deterministic")
    print("for a fixed history window.")
    return 1 if failures == len(WINDOWS) else 0


if __name__ == "__main__":
    sys.exit(main())
