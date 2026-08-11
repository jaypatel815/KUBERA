"""Compare KUBERA's strategy templates on REAL price history.

Usage:
    python scripts/backtest_demo.py            # SPY, ~2 years
    python scripts/backtest_demo.py AAPL --days 365

Needs Alpaca keys in .env (owner task T006). Data: free IEX feed, split-adjusted.
This is a research tool — backtests describe the past, never promise the future.
"""

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from backtest.engine import BacktestResult, run_backtest  # noqa: E402
from backtest.strategies import (  # noqa: E402
    buy_and_hold,
    make_mean_reversion,
    make_momentum,
    make_sma_cross,
)
from data.market_data import MarketDataClient, MarketDataError  # noqa: E402
from settings import ConfigError  # noqa: E402


def fmt(value, pct=False):
    if value is None:
        return "   n/a"
    return f"{value:6.1%}" if pct else f"{value:6.2f}"


def main() -> int:
    parser = argparse.ArgumentParser(description="KUBERA strategy comparison on real history")
    parser.add_argument("symbol", nargs="?", default="SPY")
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--cost-bps", type=float, default=5.0,
                        help="transaction cost per rebalance, basis points (default 5)")
    args = parser.parse_args()

    try:
        with MarketDataClient() as market:
            bars = market.get_daily_bars(args.symbol, days=args.days)
    except ConfigError as e:
        print(f"CONFIG: {e}")
        return 1
    except MarketDataError as e:
        print(f"DATA: {e}")
        return 1
    if len(bars.bars) < 2:
        print(f"Not enough history returned for {args.symbol!r} — check the symbol.")
        return 1

    closes = [b.close for b in bars.bars]
    dates = [b.date for b in bars.bars]
    print(f"\n{bars.symbol}: {len(closes)} trading days, {dates[0]} → {dates[-1]}"
          f"  (source: {bars.source}, fetched {bars.asof:%Y-%m-%d %H:%M UTC})\n")

    strategies = [
        buy_and_hold,
        make_momentum(lookback=60),
        make_sma_cross(fast=50, slow=200),
        make_mean_reversion(window=20, band_frac=0.05),
    ]

    header = f"{'strategy':<22} {'return':>7} {'vol':>7} {'sharpe':>7} {'max DD':>7} {'trades':>6}"
    print(header)
    print("-" * len(header))
    for strat in strategies:
        name = getattr(strat, "__name__", "strategy")
        r: BacktestResult = run_backtest(closes, dates, strat, name, cost_bps=args.cost_bps)
        print(f"{name:<22} {fmt(r.cumulative_return, pct=True)} "
              f"{fmt(r.volatility_ann, pct=True)} {fmt(r.sharpe_ann)} "
              f"{fmt(r.max_drawdown_frac, pct=True)} {r.n_rebalances:>6}")

    print("\nPast performance describes the past. Costs modeled at "
          f"{args.cost_bps:g} bps per rebalance; slippage not modeled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
