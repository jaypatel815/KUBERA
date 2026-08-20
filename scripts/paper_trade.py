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
from risk.engine import RiskEngine, RiskLimits  # noqa: E402
from settings import get_settings  # noqa: E402


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
    parser.add_argument("--after-hours", action="store_true",
                        help="bypass the market-hours guard (orders placed while "
                             "closed queue for the open print — the thing the "
                             "doctrine forbids)")
    parser.add_argument("--entry-delay", type=int, default=30, metavar="MIN",
                        help="no new buys in the first MIN minutes after the open "
                             "(doctrine: never the open print; 0 disables)")
    parser.add_argument("--event-window", type=int, default=1, metavar="DAYS",
                        help="pause new buys this many days before CPI/NFP "
                             "releases (T076)")
    parser.add_argument("--no-event-guard", action="store_true",
                        help="skip the scheduled-event pause (not recommended)")
    args = parser.parse_args()

    strategy = build_strategy(args.strategy)
    engine = make_engine()
    factory = make_session_factory(engine)
    risk = RiskEngine(limits=RiskLimits.from_settings(get_settings()))  # T115: limits from .env

    # T076: fetch the release calendar once at startup (dates don't move intraday).
    # T076b: FOMC decision days come from the published table — no key needed,
    # so the guard is NEVER fully off unless --no-event-guard says so.
    event_dates = None
    if not args.no_event_guard:
        from analysis.fomc import fomc_staleness_note, with_fomc
        from analysis.market_time import market_today
        try:
            from data.fred import FredClient  # noqa: PLC0415
            with FredClient() as fred:
                event_dates = with_fomc(fred.release_calendar())
            n = sum(len(v) for v in event_dates.values())
            print(f"event guard armed: {n} dates loaded "
                  f"(window {args.event_window}d before CPI/NFP/FOMC)")
        except Exception as e:  # noqa: BLE001 — guard is optional, never fatal
            event_dates = with_fomc(None)
            print(f"CPI/NFP calendar OFF ({type(e).__name__}: add FRED_API_KEY "
                  "to .env) — FOMC decision days still guard from the "
                  "published table")
        stale = fomc_staleness_note(market_today())
        if stale:
            print(f"NOTE: {stale}")

    while True:
        with AlpacaClient() as alpaca, MarketDataClient() as market, factory() as db:
            r = run_paper_cycle(db, alpaca, market, risk, strategy,
                                args.symbol, allocation_frac=args.allocation,
                                require_promotion=not args.skip_promotion_gate,
                                template=args.strategy,
                                enforce_market_hours=not args.after_hours,
                                entry_delay_minutes=args.entry_delay,
                                event_dates=event_dates,
                                event_window_days=args.event_window)
            print(f"[{r.action.upper()}] {args.strategy} on {r.symbol}: "
                  f"weight={r.signal_weight:.2f} current={r.current_value:.2f} "
                  f"target={r.target_value:.2f} — {r.detail}")
        if not args.loop:
            return 0
        time.sleep(args.loop)


if __name__ == "__main__":
    sys.exit(main())
