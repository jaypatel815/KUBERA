"""Run paper-trading cycles: strategy -> risk gate -> Alpaca PAPER order -> audit log.

Usage:
    python scripts/paper_trade.py SPY --strategy momentum
    python scripts/paper_trade.py AAPL --strategy sma_cross --allocation 0.10 --loop 3600

Every decision (ordered / rejected / no_action) lands in the signal_log table.
The database must exist first:  alembic -c backend/alembic.ini upgrade head
"""

import argparse
import logging
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from backtest.paper_loop import run_paper_cycle  # noqa: E402
from backtest.strategies import TEMPLATES, build_strategy  # noqa: E402
from data.alpaca import AlpacaClient  # noqa: E402
from data.db import make_engine, make_session_factory  # noqa: E402
from data.market_data import MarketDataClient  # noqa: E402
from risk.engine import RiskEngine  # noqa: E402


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description="KUBERA paper-trading loop (PAPER ONLY)")
    parser.add_argument("symbol", nargs="?", default="SPY")
    parser.add_argument("--strategy", choices=sorted(TEMPLATES), default="momentum")
    parser.add_argument("--allocation", type=float, default=0.15,
                        help="fraction of account equity this strategy may manage")
    parser.add_argument("--loop", type=int, metavar="SECONDS", default=0,
                        help="repeat every N seconds (default: one cycle)")
    parser.add_argument("--skip-promotion-gate", action="store_true",
                        help="bypass the T064 walk-forward requirement (buys only "
                             "run for promoted strategies by default — promote via "
                             "scripts/promote.py)")
    args = parser.parse_args()

    strategy = build_strategy(args.strategy)
    engine = make_engine()
    factory = make_session_factory(engine)
    risk = RiskEngine()  # per-process; trip state persistence is future work (see T032 notes)

    while True:
        with AlpacaClient() as alpaca, MarketDataClient() as market, factory() as db:
            r = run_paper_cycle(db, alpaca, market, risk, strategy,
                                args.symbol, allocation_frac=args.allocation,
                                require_promotion=not args.skip_promotion_gate,
                                template=args.strategy)
            print(f"[{r.action.upper()}] {args.strategy} on {r.symbol}: "
                  f"weight={r.signal_weight:.2f} current={r.current_value:.2f} "
                  f"target={r.target_value:.2f} — {r.detail}")
        if not args.loop:
            return 0
        time.sleep(args.loop)


if __name__ == "__main__":
    sys.exit(main())
