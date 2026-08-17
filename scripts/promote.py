"""Promotion gate CLI (T064) — earn the paper loop, don't assume it.

Runs the anchored walk-forward on real history for a (strategy, symbol) pair and
records the verdict in the backtest ledger. The paper loop refuses NEW BUYS for
unpromoted pairs (sells always work). Usage:

    python scripts\\promote.py regime_router SPY
    python scripts\\promote.py momentum SPY --days 1095 --segments 5
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backtest.ledger import promote_template  # noqa: E402
from backtest.selection_rule import SelectionRuleMissing, load_selection_rule  # noqa: E402
from backtest.strategies import TEMPLATES, build_strategy  # noqa: E402
from data.db import make_engine, make_session_factory  # noqa: E402
from data.market_data import MarketDataClient  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the T064 walk-forward promotion gate.")
    ap.add_argument("strategy", choices=sorted(TEMPLATES))
    ap.add_argument("symbol", nargs="?", default="SPY")
    ap.add_argument("--days", type=int, default=730)
    ap.add_argument("--segments", type=int, default=4)
    ap.add_argument("--cost-bps", type=float, default=5.0)
    args = ap.parse_args()

    # T109/D029: promotion is judged against the PRE-REGISTERED standard, and
    # refuses to run without one. The rule's version is stamped on the record.
    try:
        rule = load_selection_rule()
    except SelectionRuleMissing as e:
        print(str(e))
        return 2
    print(f"applying selection rule {rule.version} ({rule.path})")

    engine = make_engine()
    factory = make_session_factory(engine)
    with MarketDataClient() as market, factory() as db:
        wf, row = promote_template(
            db, market, build_strategy(args.strategy), args.strategy,
            args.symbol, days=args.days, n_segments=args.segments,
            cost_bps=args.cost_bps, rule_version=rule.version,
        )
    verdict = "PASSED" if wf.passed else "FAILED"
    print(f"{verdict} — {args.strategy} on {row.symbol} "
          f"({row.start_date} → {row.end_date}, run #{row.id})")
    print(f"  overall return: {wf.overall_return:+.2%}")
    for i, r in enumerate(wf.segment_returns, 1):
        print(f"  segment {i}/{wf.n_segments}: {r:+.2%}")
    print(f"  criteria: {wf.criteria}")
    if not wf.passed:
        print("  -> the paper loop will refuse new buys for this pair "
              "(that is the point)")
    return 0 if wf.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
