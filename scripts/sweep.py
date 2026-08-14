"""T092 — parameter stability sweep: is this template edge, or curve-fit?

Sweeps a strategy template across its parameter neighborhood on real history
and prints the verdict. A promotion without a stability check is a backtest
that memorized one number.

Usage (owner machine, venv active):
    python scripts\\sweep.py momentum SPY
    python scripts\\sweep.py mean_reversion AAPL --days 500 --record

--record attaches the report to the latest ledger run for (template, symbol)
(run a backtest or promotion first) so the evidence sits beside the promotion.
"""

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backtest.stability import SWEEPS, run_sweep  # noqa: E402
from data.db import make_engine, make_session_factory  # noqa: E402
from data.market_data import MarketDataClient  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("template", choices=sorted(SWEEPS))
    ap.add_argument("symbol")
    ap.add_argument("--days", type=int, default=750)
    ap.add_argument("--cost-bps", type=float, default=5.0)
    ap.add_argument("--record", action="store_true",
                    help="attach the report to the latest ledger run")
    args = ap.parse_args()

    with MarketDataClient() as market:
        bars = market.get_daily_bars(args.symbol, days=args.days)
    closes = [b.close for b in bars.bars]
    dates = [b.date for b in bars.bars]
    print(f"{args.template} on {args.symbol.upper()}: {len(closes)} bars "
          f"({dates[0]} → {dates[-1]}), cost {args.cost_bps}bps")

    report = run_sweep(closes, dates, args.template, cost_bps=args.cost_bps)
    print(f"\n  {report.param_name:>10} | sharpe")
    for row in report.results:
        marker = "  <- best" if row["param"] == report.best_param else ""
        print(f"  {row['param']:>10} | {row['metric']:+.2f}{marker}")
    print(f"\n  median {report.median_metric:+.2f} · neighbor support "
          f"{report.support_frac:.0%} · VERDICT: {report.verdict.upper()}")
    print(f"  {report.note}")
    for w in report.warnings:
        print(f"  ! {w}")

    if args.record:
        engine = make_engine()
        with make_session_factory(engine)() as db:
            from backtest.ledger import attach_stability  # noqa: PLC0415
            run_id = attach_stability(db, args.template, args.symbol,
                                      asdict(report))
            print(f"\n  recorded on ledger run #{run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
